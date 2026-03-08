"""RFI V2 핵심 서비스 — 질의 원장 CRUD + 스레드 이력 + 낙관적 락."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import AuditAction, RFIAuthorRole, RFIItemStatusV2
from app.models.rfi_item_v2 import RFIItemV2
from app.models.rfi_thread import RFIThread
from app.schemas.rfi_v2 import (
    RFICategoryBreakdown,
    RFIDashboardSummary,
    RFIItemCreateV2,
    RFIItemListOut,
    RFIItemUpdateV2,
    RFIReportPayload,
    RFIThreadCreate,
    RFIVerifiedFact,
)
from app.services import audit_service

logger = logging.getLogger(__name__)

# ── Item Number 채번 ──────────────────────────────────────


async def _next_item_number(db: AsyncSession, txn_id: uuid.UUID) -> str:
    """RFI-YYYY-NNN 형식 채번."""
    year = datetime.now(UTC).year
    result = await db.execute(select(func.count(RFIItemV2.id)).where(RFIItemV2.transaction_id == txn_id))
    seq = (result.scalar() or 0) + 1
    return f"RFI-{year}-{seq:03d}"


# ── Item CRUD ─────────────────────────────────────────────


async def list_items(
    db: AsyncSession,
    txn_id: uuid.UUID,
    *,
    category: str | None = None,
    item_status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    is_advisor: bool = True,
) -> list[RFIItemV2]:
    """질의 목록 조회 (소프트 삭제 제외, 필터링)."""
    q = select(RFIItemV2).where(
        RFIItemV2.transaction_id == txn_id,
        RFIItemV2.is_deleted.is_(False),
    )

    if category:
        q = q.where(RFIItemV2.category == category)
    if item_status:
        q = q.where(RFIItemV2.current_status == item_status)
    if priority:
        q = q.where(RFIItemV2.priority == priority)
    if search:
        escaped = search.replace("%", r"\%").replace("_", r"\_")
        q = q.where(RFIItemV2.question_text.ilike(f"%{escaped}%", escape="\\"))

    q = (
        q.options(
            selectinload(RFIItemV2.threads),
            selectinload(RFIItemV2.attachments),
        )
        .order_by(RFIItemV2.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    items = list(result.scalars().all())

    # TARGET은 internal_memo 숨김 — ORM 객체를 세션에서 분리하여 DB 영속화 방지
    if not is_advisor:
        for item in items:
            db.expunge(item)
            item.internal_memo = None

    return items


async def get_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    is_advisor: bool = True,
) -> RFIItemV2:
    """단일 질의 상세 조회 (threads + attachments 포함)."""
    q = (
        select(RFIItemV2)
        .options(
            selectinload(RFIItemV2.threads).selectinload(RFIThread.attachments),
            selectinload(RFIItemV2.attachments),
        )
        .where(
            RFIItemV2.id == item_id,
            RFIItemV2.transaction_id == txn_id,
            RFIItemV2.is_deleted.is_(False),
        )
    )
    result = await db.execute(q)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFI 항목을 찾을 수 없습니다")

    # TARGET은 internal_memo 숨김 — ORM 객체를 세션에서 분리하여 DB 영속화 방지
    if not is_advisor:
        db.expunge(item)
        item.internal_memo = None

    return item


async def create_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    payload: RFIItemCreateV2,
    *,
    created_by: str | None = None,
) -> RFIItemV2:
    """질의 항목 생성."""
    item_number = await _next_item_number(db, txn_id)
    item = RFIItemV2(
        transaction_id=txn_id,
        item_number=item_number,
        category=payload.category,
        priority=payload.priority,
        target_doc=payload.target_doc,
        question_text=payload.question_text,
        internal_memo=payload.internal_memo,
        report_section_tag=payload.report_section_tag,
        assignee_email=payload.assignee_email,
        due_date=payload.due_date,
        created_by_email=created_by,
    )
    db.add(item)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.CREATE, "rfi_item", str(item.id), created_by)
    logger.info("RFI 항목 생성: txn=%s, item=%s, number=%s", txn_id, item.id, item.item_number)
    return item


async def create_items_batch(
    db: AsyncSession,
    txn_id: uuid.UUID,
    items: list[RFIItemCreateV2],
    *,
    created_by: str | None = None,
) -> list[RFIItemV2]:
    """질의 항목 일괄 생성."""
    created = []
    for payload in items:
        item = await create_item(db, txn_id, payload, created_by=created_by)
        created.append(item)
    return created


async def update_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: RFIItemUpdateV2,
    *,
    updated_by: str | None = None,
) -> RFIItemV2:
    """질의 항목 수정 (낙관적 락 검증)."""
    item = await get_item(db, txn_id, item_id)

    # 낙관적 락 검증
    if item.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="다른 사용자가 이 항목을 수정했습니다. 새로고침 후 다시 시도하세요.",
        )

    update_data = payload.model_dump(exclude_unset=True, exclude={"version"})
    for key, value in update_data.items():
        setattr(item, key, value)

    item.version += 1
    item.updated_at = datetime.now(UTC)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.UPDATE, "rfi_item", str(item.id), updated_by)
    logger.info("RFI 항목 수정: txn=%s, item=%s, version=%d", txn_id, item.id, item.version)
    return item


async def soft_delete_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    deleted_by: str | None = None,
) -> None:
    """소프트 삭제 (OPEN 상태만 허용)."""
    item = await get_item(db, txn_id, item_id)
    if item.current_status != RFIItemStatusV2.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OPEN 상태의 항목만 삭제할 수 있습니다",
        )
    item.is_deleted = True
    item.updated_at = datetime.now(UTC)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.DELETE, "rfi_item", str(item.id), deleted_by)
    logger.info("RFI 항목 삭제: txn=%s, item=%s", txn_id, item.id)


async def close_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    version: int,
    *,
    closed_by: str | None = None,
) -> RFIItemV2:
    """CLOSED 상태 전환."""
    item = await get_item(db, txn_id, item_id)
    if item.version != version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="다른 사용자가 이 항목을 수정했습니다. 새로고침 후 다시 시도하세요.",
        )
    item.current_status = RFIItemStatusV2.CLOSED
    item.version += 1
    item.updated_at = datetime.now(UTC)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.UPDATE, "rfi_item", str(item.id), closed_by)
    logger.info("RFI 항목 마감: txn=%s, item=%s", txn_id, item.id)
    return item


# ── Thread CRUD ───────────────────────────────────────────


async def list_threads(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
) -> list[RFIThread]:
    """스레드 이력 조회 — item이 해당 txn에 속하는지 검증."""
    # item 소유권 검증
    await get_item(db, txn_id, item_id)
    result = await db.execute(select(RFIThread).where(RFIThread.item_id == item_id).order_by(RFIThread.round_num))
    return list(result.scalars().all())


async def create_thread(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: RFIThreadCreate,
    *,
    author_email: str,
    author_role: RFIAuthorRole,
) -> RFIThread:
    """답변/추가질의 작성 — 자동 상태 전환."""
    item = await get_item(db, txn_id, item_id)

    if item.current_status == RFIItemStatusV2.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CLOSED 상태에서는 답변을 추가할 수 없습니다",
        )

    # 다음 round_num 계산
    max_round = await db.execute(select(func.max(RFIThread.round_num)).where(RFIThread.item_id == item_id))
    next_round = (max_round.scalar() or 0) + 1

    thread = RFIThread(
        item_id=item_id,
        round_num=next_round,
        author_email=author_email,
        author_role=author_role,
        content_text=payload.content_text,
        is_published=payload.is_published,
    )
    db.add(thread)

    # 상태 자동 전환
    if author_role == RFIAuthorRole.TARGET:
        item.current_status = RFIItemStatusV2.ANSWERED
    elif author_role == RFIAuthorRole.ADVISOR and item.current_status == RFIItemStatusV2.ANSWERED:
        item.current_status = RFIItemStatusV2.CLARIFICATION_NEEDED

    item.version += 1
    item.updated_at = datetime.now(UTC)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.CREATE, "rfi_thread", str(thread.id), author_email)
    logger.info("RFI 스레드 생성: txn=%s, item=%s, thread=%s, round=%d", txn_id, item_id, thread.id, next_round)
    return thread


async def update_thread_publish(
    db: AsyncSession,
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    thread_id: uuid.UUID,
    is_published: bool,
) -> RFIThread:
    """임시저장 → 게시 전환 — item/txn 소유권 검증 포함."""
    await get_item(db, txn_id, item_id)
    result = await db.execute(select(RFIThread).where(RFIThread.id == thread_id, RFIThread.item_id == item_id))
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스레드를 찾을 수 없습니다")

    thread.is_published = is_published
    await db.flush()
    return thread


# ── Dashboard ─────────────────────────────────────────────


async def get_dashboard(db: AsyncSession, txn_id: uuid.UUID) -> RFIDashboardSummary:
    """RFI 대시보드 통계."""
    base = select(RFIItemV2).where(
        RFIItemV2.transaction_id == txn_id,
        RFIItemV2.is_deleted.is_(False),
    )

    # 전체 항목
    all_items_result = await db.execute(base)
    all_items = list(all_items_result.scalars().all())
    total = len(all_items)

    # 상태별 집계
    status_counts: dict[str, int] = {}
    for s in RFIItemStatusV2:
        status_counts[s.value] = sum(1 for i in all_items if i.current_status == s)

    # 카테고리별 분석
    category_breakdown: list[RFICategoryBreakdown] = []
    categories = {i.category for i in all_items}
    for cat in sorted(categories, key=lambda c: c.value):
        cat_items = [i for i in all_items if i.category == cat]
        cat_total = len(cat_items)
        answered = sum(1 for i in cat_items if i.current_status == RFIItemStatusV2.ANSWERED)
        closed = sum(1 for i in cat_items if i.current_status == RFIItemStatusV2.CLOSED)
        open_count = sum(1 for i in cat_items if i.current_status == RFIItemStatusV2.OPEN)
        clarification = sum(1 for i in cat_items if i.current_status == RFIItemStatusV2.CLARIFICATION_NEEDED)
        category_breakdown.append(
            RFICategoryBreakdown(
                category=cat.value,
                total=cat_total,
                open=open_count,
                answered=answered,
                closed=closed,
                clarification_needed=clarification,
                response_pct=round((answered + closed) / cat_total * 100, 1) if cat_total else 0.0,
            )
        )

    # 에이징: OPEN 상태 + 7일 이상 경과
    now = datetime.now(UTC)
    aging_items: list[RFIItemListOut] = []
    for item in all_items:
        if item.current_status == RFIItemStatusV2.OPEN and item.created_at:
            created = item.created_at if item.created_at.tzinfo else item.created_at.replace(tzinfo=UTC)
            age = (now - created).days
            if age >= 7:
                aging_items.append(RFIItemListOut.model_validate(item))

    return RFIDashboardSummary(
        total_items=total,
        status_counts=status_counts,
        category_breakdown=category_breakdown,
        aging_items=aging_items,
    )


# ── Report Bridge ─────────────────────────────────────────


async def get_report_payload(db: AsyncSession, txn_id: uuid.UUID) -> list[RFIReportPayload]:
    """LLM용 보고서 데이터 추출 — ANSWERED/CLOSED만."""
    q = (
        select(RFIItemV2)
        .options(
            selectinload(RFIItemV2.threads).selectinload(RFIThread.attachments),
        )
        .where(
            RFIItemV2.transaction_id == txn_id,
            RFIItemV2.is_deleted.is_(False),
            RFIItemV2.current_status.in_([RFIItemStatusV2.ANSWERED, RFIItemStatusV2.CLOSED]),
        )
    )
    result = await db.execute(q)
    items = list(result.scalars().all())

    # report_section_tag 기준 그룹화
    sections: dict[str, list[RFIItemV2]] = {}
    for item in items:
        tag = item.report_section_tag or "UNCATEGORIZED"
        sections.setdefault(tag, []).append(item)

    payloads: list[RFIReportPayload] = []
    for section, section_items in sections.items():
        facts: list[RFIVerifiedFact] = []
        for item in section_items:
            target_answers = [
                t.content_text for t in item.threads if t.author_role == RFIAuthorRole.TARGET and t.is_published
            ]
            vdr_files = [a.file_name for t in item.threads for a in t.attachments]
            facts.append(
                RFIVerifiedFact(
                    original_question=item.question_text,
                    target_company_answers=target_answers,
                    referenced_vdr_files=vdr_files,
                )
            )
        payloads.append(RFIReportPayload(report_section=section, verified_facts=facts))

    return payloads
