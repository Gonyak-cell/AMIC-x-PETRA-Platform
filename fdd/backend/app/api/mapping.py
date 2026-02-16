"""Mapping API — FDD-302, FDD-303.

CoA 매핑 제안, 저장, 승인, 조회 + Tie-out 검증 엔드포인트.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.deal import Deal
from app.models.journal_entry import JournalEntry
from app.models.standard_line_item import StandardLineItem
from app.models.tie_out import TieOutResult
from app.schemas.mapping import (
    AccountMappingApprove,
    AccountMappingRead,
    AccountMappingUpdate,
    MappingBulkCreate,
    MappingSuggestion,
    StandardLineItemRead,
    TieOutResultRead,
    TieOutRun,
)
from app.services.mapping.coa_mapper import (
    approve_mapping,
    save_mappings,
    suggest_mappings,
)
from app.services.mapping.tie_out import validate_tie_out

router = APIRouter()


# ── Standard Line Items ──────────────────────────────────


@router.get(
    "/standard-line-items",
    response_model=list[StandardLineItemRead],
)
def list_standard_line_items(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """표준 라인아이템 전체 조회."""
    stmt = select(StandardLineItem).order_by(StandardLineItem.display_order)
    return list(db.scalars(stmt).all())


# ── Mapping Suggest ──────────────────────────────────────


@router.post(
    "/deals/{deal_id}/mappings/suggest",
    response_model=list[MappingSuggestion],
)
def suggest_account_mappings(
    deal_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """TB 계정에 대한 매핑 제안을 생성한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    # 표준 라인아이템 조회
    line_items = list(db.scalars(select(StandardLineItem)).all())
    if not line_items:
        raise HTTPException(
            status_code=400,
            detail="Standard line items not seeded. Run seed first.",
        )

    # TB 계정별 잔액 집계 (SQLite 호환 — DISTINCT ON 미사용)
    tb_stmt = (
        select(
            JournalEntry.account_code,
            func.min(JournalEntry.account_name).label("account_name"),
            func.sum(JournalEntry.balance).label("balance"),
        )
        .where(
            JournalEntry.deal_id == deal_id,
            JournalEntry.source_type == "TB",
            JournalEntry.account_code.isnot(None),
        )
        .group_by(JournalEntry.account_code)
    )
    rows = db.execute(tb_stmt).all()

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="No TB data found for this deal. Upload and ingest a TB file first.",
        )

    tb_accounts: list[tuple[str, str, Decimal]] = [
        (
            row.account_code or "",
            row.account_name or "",
            row.balance or Decimal("0"),
        )
        for row in rows
        if row.account_code
    ]

    suggestions = suggest_mappings(line_items, tb_accounts)
    return suggestions


# ── Mapping CRUD ─────────────────────────────────────────


@router.post(
    "/deals/{deal_id}/mappings",
    response_model=list[AccountMappingRead],
    status_code=201,
)
def create_mappings_bulk(
    deal_id: uuid.UUID,
    body: MappingBulkCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """매핑을 일괄 저장한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    saved = save_mappings(db, deal_id, body.mappings)
    return saved


@router.get(
    "/deals/{deal_id}/mappings",
    response_model=list[AccountMappingRead],
)
def list_mappings(
    deal_id: uuid.UUID,
    status: MappingStatus | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """딜의 매핑 목록을 조회한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    stmt = select(AccountMapping).where(AccountMapping.deal_id == deal_id)
    if status is not None:
        stmt = stmt.where(AccountMapping.status == status)
    stmt = stmt.order_by(AccountMapping.source_account_code)

    return list(db.scalars(stmt).all())


@router.get(
    "/deals/{deal_id}/mappings/{mapping_id}",
    response_model=AccountMappingRead,
)
def get_mapping(
    deal_id: uuid.UUID,
    mapping_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """단일 매핑을 조회한다."""
    mapping = db.get(AccountMapping, mapping_id)
    if mapping is None or mapping.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.put(
    "/deals/{deal_id}/mappings/{mapping_id}",
    response_model=AccountMappingRead,
)
def update_mapping(
    deal_id: uuid.UUID,
    mapping_id: uuid.UUID,
    body: AccountMappingUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """매핑 정보를 수정한다 (대상 변경, 상태 변경 등)."""
    mapping = db.get(AccountMapping, mapping_id)
    if mapping is None or mapping.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Mapping not found")

    if body.target_line_item_code is not None:
        mapping.target_line_item_code = body.target_line_item_code
    if body.status is not None:
        mapping.status = body.status
    if body.rejection_reason is not None:
        mapping.rejection_reason = body.rejection_reason

    db.commit()
    db.refresh(mapping)
    return mapping


@router.post(
    "/deals/{deal_id}/mappings/{mapping_id}/approve",
    response_model=AccountMappingRead,
)
def approve_mapping_endpoint(
    deal_id: uuid.UUID,
    mapping_id: uuid.UUID,
    body: AccountMappingApprove,
    current_user: CurrentUser = require_permission(Permission.MAPPING_APPROVE),
    db: Session = Depends(get_db),
):
    """매핑을 승인한다."""
    mapping = db.get(AccountMapping, mapping_id)
    if mapping is None or mapping.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Mapping not found")

    if mapping.status == MappingStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Mapping already approved")

    approved = approve_mapping(db, mapping, body.approved_by)
    return approved


@router.post(
    "/deals/{deal_id}/mappings/approve-all",
    response_model=list[AccountMappingRead],
)
def approve_all_proposed(
    deal_id: uuid.UUID,
    body: AccountMappingApprove,
    current_user: CurrentUser = require_permission(Permission.MAPPING_APPROVE),
    db: Session = Depends(get_db),
):
    """PROPOSED 상태의 모든 매핑을 일괄 승인한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    stmt = select(AccountMapping).where(
        AccountMapping.deal_id == deal_id,
        AccountMapping.status == MappingStatus.PROPOSED,
    )
    proposed = list(db.scalars(stmt))

    if not proposed:
        raise HTTPException(status_code=400, detail="No proposed mappings to approve")

    approved_list: list[AccountMapping] = []
    for mapping in proposed:
        approved = approve_mapping(db, mapping, body.approved_by)
        approved_list.append(approved)

    return approved_list


# ── Tie-out ──────────────────────────────────────────────


@router.post(
    "/deals/{deal_id}/tie-out/validate",
    response_model=list[TieOutResultRead],
)
def run_tie_out(
    deal_id: uuid.UUID,
    body: TieOutRun,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """IS/BS Tie-out 검증을 실행한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    is_result, bs_result = validate_tie_out(db, deal_id, body.snapshot_id)
    return [is_result, bs_result]


@router.get(
    "/deals/{deal_id}/tie-out",
    response_model=list[TieOutResultRead],
)
def list_tie_out_results(
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tie-out 결과 목록을 조회한다."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    stmt = select(TieOutResult).where(TieOutResult.deal_id == deal_id)
    if snapshot_id is not None:
        stmt = stmt.where(TieOutResult.snapshot_id == snapshot_id)
    stmt = stmt.order_by(TieOutResult.created_at.desc())

    return list(db.scalars(stmt).all())
