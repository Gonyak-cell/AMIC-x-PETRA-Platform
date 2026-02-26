"""컴플라이언스 체크리스트 라우터."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.compliance_item import ComplianceItem
from app.models.enums import AuditAction, ComplianceStatus
from app.schemas.compliance import (
    ComplianceCategorySummary,
    ComplianceItemCreate,
    ComplianceItemOut,
    ComplianceItemUpdate,
    ComplianceSummary,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/compliance", tags=["Compliance"])


@router.get("", response_model=list[ComplianceItemOut])
async def list_compliance(
    txn_id: uuid.UUID,
    category: str | None = None,
    compliance_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(ComplianceItem).where(ComplianceItem.transaction_id == txn_id)
    if category:
        q = q.where(ComplianceItem.category == category)
    if compliance_status:
        q = q.where(ComplianceItem.status == compliance_status)
    q = q.order_by(ComplianceItem.category, ComplianceItem.created_at)
    result = await db.execute(q)
    return [ComplianceItemOut.model_validate(c) for c in result.scalars().all()]


@router.get("/summary", response_model=ComplianceSummary)
async def compliance_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(ComplianceItem).where(ComplianceItem.transaction_id == txn_id)
    result = await db.execute(q)
    items = list(result.scalars().all())

    # by_category
    cat_map: dict[str, dict[str, int]] = {}
    for item in items:
        cat = item.category.value
        if cat not in cat_map:
            cat_map[cat] = {"total": 0, "approved": 0, "flagged": 0, "pending": 0}
        cat_map[cat]["total"] += 1
        if item.status == ComplianceStatus.APPROVED:
            cat_map[cat]["approved"] += 1
        elif item.status in (ComplianceStatus.FLAGGED, ComplianceStatus.NON_COMPLIANT):
            cat_map[cat]["flagged"] += 1
        elif item.status in (
            ComplianceStatus.NOT_STARTED,
            ComplianceStatus.IN_REVIEW,
            ComplianceStatus.PENDING_APPROVAL,
        ):
            cat_map[cat]["pending"] += 1

    by_category = [ComplianceCategorySummary(category=cat, **counts) for cat, counts in cat_map.items()]

    # by_status
    status_counter = Counter(item.status.value for item in items)

    # compliance_rate
    approved_or_waived = sum(1 for item in items if item.status in (ComplianceStatus.APPROVED, ComplianceStatus.WAIVED))
    compliance_rate = (approved_or_waived / len(items) * 100) if items else 0.0

    # flagged & overdue counts
    flagged_count = sum(
        1 for item in items if item.status in (ComplianceStatus.FLAGGED, ComplianceStatus.NON_COMPLIANT)
    )
    today = date.today().isoformat()
    overdue_count = sum(
        1
        for item in items
        if item.due_date
        and item.due_date < today
        and item.status not in (ComplianceStatus.APPROVED, ComplianceStatus.WAIVED)
    )

    return ComplianceSummary(
        total=len(items),
        by_category=by_category,
        by_status=dict(status_counter),
        compliance_rate=round(compliance_rate, 1),
        flagged_count=flagged_count,
        overdue_count=overdue_count,
    )


@router.post("", response_model=ComplianceItemOut, status_code=201)
async def create_compliance(
    txn_id: uuid.UUID,
    body: ComplianceItemCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    item = ComplianceItem(transaction_id=txn_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="ComplianceItem",
        entity_id=item.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(item)
    return ComplianceItemOut.model_validate(item)


@router.get("/{item_id}", response_model=ComplianceItemOut)
async def get_compliance(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await check_client_deal_access(db, txn_id, claims)
    q = select(ComplianceItem).where(ComplianceItem.id == item_id, ComplianceItem.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="컴플라이언스 항목을 찾을 수 없습니다")
    return ComplianceItemOut.model_validate(item)


@router.patch("/{item_id}", response_model=ComplianceItemOut)
async def update_compliance(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ComplianceItemUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(ComplianceItem).where(ComplianceItem.id == item_id, ComplianceItem.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="컴플라이언스 항목을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    await audit_service.record(
        db,
        entity_type="ComplianceItem",
        entity_id=item.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(item)
    return ComplianceItemOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_compliance(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(ComplianceItem).where(ComplianceItem.id == item_id, ComplianceItem.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="컴플라이언스 항목을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="ComplianceItem",
        entity_id=item.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(item)
    await db.commit()
