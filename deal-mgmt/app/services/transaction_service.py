"""Transaction CRUD 비즈니스 로직."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.closing_checklist import ClosingChecklist
from app.models.enums import AuditAction, ClosingCategory, DealType, TransactionPhase, TransactionStatus
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services import audit_service


def _get_code_prefix(deal_type: DealType) -> str:
    if deal_type == DealType.ISSUE:
        return "ISU"
    return deal_type.value


def _get_code_prefix_candidates(deal_type: DealType) -> list[str]:
    primary = _get_code_prefix(deal_type)
    if deal_type == DealType.ISSUE:
        return [primary, DealType.ISSUE.value]
    return [primary]


async def _generate_code_name(
    db: AsyncSession,
    deal_type: DealType,
    project_name: str,
    year: int,
) -> str:
    """코드명 자동 생성 — 삭제된 행 포함 MAX 시퀀스 기반.

    형식: {TYPE}{YY}-{ABB}-{NN}
    예시: SE26-EDW-01 (2026년 첫 번째 매각 자문 딜, Project Edward)
    """
    import re

    abbr = project_name.removeprefix("Project ").strip()[:3].upper()
    year_suffix = str(year)[2:]
    prefix = f"{_get_code_prefix(deal_type)}{year_suffix}-{abbr}-"
    prefix_candidates = [f"{candidate}{year_suffix}-{abbr}-" for candidate in _get_code_prefix_candidates(deal_type)]

    result = await db.execute(
        select(Transaction.code_name).where(
            or_(*[Transaction.code_name.like(f"{candidate}%") for candidate in prefix_candidates]),
        )
    )
    existing = [row[0] for row in result.all()]

    max_seq = 0
    for name in existing:
        m = re.search(r"-(\d+)$", name)
        if m:
            max_seq = max(max_seq, int(m.group(1)))

    return f"{prefix}{max_seq + 1:02d}"


# M&A Closing에서 공통으로 요구되는 표준 체크리스트 항목
_STANDARD_CLOSING_ITEMS: list[dict] = [
    # 선행 조건
    {
        "category": ClosingCategory.CONDITION_PRECEDENT,
        "title": "선행 조건 충족 확인 (CP Satisfaction)",
        "description": "SPA에 명시된 모든 선행 조건이 충족됐는지 확인",
        "sort_order": 10,
    },
    {
        "category": ClosingCategory.CONDITION_PRECEDENT,
        "title": "진술 및 보장 재확인 (Reps & Warranties)",
        "description": "Closing일 기준 진술 및 보장이 여전히 진실하고 정확한지 확인",
        "sort_order": 20,
    },
    {
        "category": ClosingCategory.CONDITION_PRECEDENT,
        "title": "중요 계약 동의 획득 (Material Consents)",
        "description": "주요 계약의 변경통제 조항에 따른 거래상대방 동의 획득",
        "sort_order": 30,
    },
    # 규제
    {
        "category": ClosingCategory.REGULATORY,
        "title": "공정거래위원회 기업결합 신고",
        "description": "기업결합 신고 대상 여부 확인 및 해당 시 신고/승인 획득",
        "sort_order": 10,
    },
    {
        "category": ClosingCategory.REGULATORY,
        "title": "외국인투자신고 (FDI Review)",
        "description": "외국인 투자자 관련 신고/승인 요건 확인 및 처리",
        "sort_order": 20,
    },
    # 법적
    {
        "category": ClosingCategory.LEGAL,
        "title": "SPA 최종 서명 완료",
        "description": "주식매매계약서(SPA) 모든 당사자 서명 완료",
        "sort_order": 10,
    },
    {
        "category": ClosingCategory.LEGAL,
        "title": "주주총회/이사회 결의",
        "description": "거래 승인을 위한 주주총회 및 이사회 결의 완료",
        "sort_order": 20,
    },
    {
        "category": ClosingCategory.LEGAL,
        "title": "주식 양도 관련 서류 준비",
        "description": "명의개서청구서 등 주식 이전 법적 서류 준비 완료",
        "sort_order": 30,
    },
    # 재무
    {
        "category": ClosingCategory.FINANCIAL,
        "title": "거래대금 지급 계좌 확인",
        "description": "매도인 지급 계좌 정보 확인 및 검증",
        "sort_order": 10,
    },
    {
        "category": ClosingCategory.FINANCIAL,
        "title": "에스크로 계좌 설정",
        "description": "진술보장 손해배상 등을 위한 에스크로 계좌 개설 (해당 시)",
        "sort_order": 20,
    },
    {
        "category": ClosingCategory.FINANCIAL,
        "title": "Net Debt / Working Capital 최종 정산",
        "description": "Closing일 기준 순차입금 및 운전자본 확정 및 조정",
        "sort_order": 30,
    },
    # 법인
    {
        "category": ClosingCategory.CORPORATE,
        "title": "이사회 구성 변경 준비",
        "description": "인수 후 이사진 변경 서류 및 등기 준비",
        "sort_order": 10,
    },
    {
        "category": ClosingCategory.CORPORATE,
        "title": "법인등기 및 사업자등록 변경",
        "description": "대표이사 변경 등 법인등기 및 사업자등록 변경 준비",
        "sort_order": 20,
    },
    # 자금 집행
    {
        "category": ClosingCategory.FUND_FLOW,
        "title": "Closing일 거래대금 집행",
        "description": "Closing 당일 거래대금 전액 집행 및 에스크로 이체 확인",
        "sort_order": 10,
    },
    {
        "category": ClosingCategory.FUND_FLOW,
        "title": "원천징수세 처리",
        "description": "대금 지급 시 원천징수세 처리 방법 확인 및 집행",
        "sort_order": 20,
    },
]


async def list_transactions(
    db: AsyncSession,
    *,
    search: str | None = None,
    side: str | None = None,
    phase: str | None = None,
    tx_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    client_email: str | None = None,
    assigned_to_email: str | None = None,
) -> tuple[list[Transaction], int]:
    """거래 목록 조회 (필터/검색/페이지네이션).

    client_email이 주어지면 해당 이메일이 배정된 딜만 반환한다 (CLIENT 역할용).
    assigned_to_email이 주어지면 lead_advisor, deal_captain, 또는 working_group 멤버인 딜만 반환한다.
    """
    from app.models.deal_client import DealClient
    from app.models.working_group import WorkingGroupMember

    base = select(Transaction).where(Transaction.is_deleted.is_(False))

    if client_email is not None:
        base = base.where(Transaction.id.in_(select(DealClient.transaction_id).where(DealClient.email == client_email)))

    if assigned_to_email is not None:
        email_lower = func.lower(assigned_to_email)
        wg_subq = select(WorkingGroupMember.transaction_id).where(
            func.lower(WorkingGroupMember.email) == email_lower,
            WorkingGroupMember.is_active.is_(True),
        )
        base = base.where(
            or_(
                func.lower(Transaction.lead_advisor_email) == email_lower,
                func.lower(Transaction.deal_captain_email) == email_lower,
                Transaction.id.in_(wg_subq),
            )
        )

    if search:
        pattern = f"%{search}%"
        base = base.where(
            Transaction.name.ilike(pattern)
            | Transaction.code_name.ilike(pattern)
            | Transaction.target_company_name.ilike(pattern)
            | Transaction.client_name.ilike(pattern)
        )
    if side:
        base = base.where(Transaction.side == side)
    if phase:
        base = base.where(Transaction.phase == phase)
    if tx_status:
        base = base.where(Transaction.status == tx_status)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(Transaction.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(rows_q)
    return list(result.scalars().all()), total


async def get_transaction(db: AsyncSession, txn_id: uuid.UUID) -> Transaction:
    """단건 조회 — 없으면 404."""
    q = select(Transaction).where(Transaction.id == txn_id, Transaction.is_deleted.is_(False))
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="거래를 찾을 수 없습니다")
    return row


async def create_transaction(
    db: AsyncSession,
    body: TransactionCreate,
    actor_email: str | None = None,
) -> Transaction:
    """거래 생성 — 코드명 자동 부여."""
    year = datetime.now().year
    code_name = await _generate_code_name(db, body.deal_type, body.name, year)
    data = body.model_dump()

    txn = Transaction(
        **data,
        code_name=code_name,
        phase=TransactionPhase.ENGAGEMENT,
        status=TransactionStatus.DRAFT,
    )
    db.add(txn)
    try:
        await db.flush()
    except IntegrityError:
        # 동시 생성으로 인한 UniqueConstraint 충돌 — seq+1로 1회 재시도
        await db.rollback()
        code_name = await _generate_code_name(db, body.deal_type, body.name, year)
        txn = Transaction(
            **data,
            code_name=code_name,
            phase=TransactionPhase.ENGAGEMENT,
            status=TransactionStatus.DRAFT,
        )
        db.add(txn)
        await db.flush()

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.CREATE,
        actor_email=actor_email,
        new_value={**data, "code_name": code_name},
    )

    # 표준 Closing 체크리스트 자동 생성
    for item_data in _STANDARD_CLOSING_ITEMS:
        db.add(ClosingChecklist(transaction_id=txn.id, **item_data))

    # VDR 기본 폴더 자동 생성 (12개)
    from app.services.vdr_service import create_default_folders

    create_default_folders(db, txn.id)

    await db.commit()
    await db.refresh(txn)
    return txn


async def update_transaction(
    db: AsyncSession,
    txn_id: uuid.UUID,
    body: TransactionUpdate,
    actor_email: str | None = None,
) -> Transaction:
    """거래 수정."""
    txn = await get_transaction(db, txn_id)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return txn

    old_value = {k: getattr(txn, k) for k in update_data}
    for k, v in update_data.items():
        setattr(txn, k, v)

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.UPDATE,
        actor_email=actor_email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(txn)
    return txn


async def delete_transaction(
    db: AsyncSession,
    txn_id: uuid.UUID,
    actor_email: str | None = None,
) -> None:
    """소프트 삭제."""
    txn = await get_transaction(db, txn_id)
    txn.is_deleted = True

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.DELETE,
        actor_email=actor_email,
    )
    await db.commit()
