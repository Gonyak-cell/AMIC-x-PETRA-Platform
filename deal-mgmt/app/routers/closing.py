"""클로징 체크리스트 관리 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.closing_checklist import ClosingChecklist
from app.models.enums import AuditAction, ClosingConditionStatus
from app.schemas.closing import (
    ClosingChecklistCreate,
    ClosingChecklistOut,
    ClosingChecklistSummary,
    ClosingChecklistUpdate,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/closing", tags=["Closing"])


@router.get("", response_model=list[ClosingChecklistOut])
async def list_closing_items(
    txn_id: uuid.UUID,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(ClosingChecklist).where(ClosingChecklist.transaction_id == txn_id)
    if category:
        q = q.where(ClosingChecklist.category == category)
    q = q.order_by(ClosingChecklist.sort_order, ClosingChecklist.created_at.desc())
    result = await db.execute(q)
    return [ClosingChecklistOut.model_validate(c) for c in result.scalars().all()]


@router.get("/summary", response_model=ClosingChecklistSummary)
async def closing_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(ClosingChecklist).where(ClosingChecklist.transaction_id == txn_id)
    result = await db.execute(q)
    items = list(result.scalars().all())

    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    completed = 0
    for item in items:
        by_category[item.category.value] = by_category.get(item.category.value, 0) + 1
        by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
        if item.status in (ClosingConditionStatus.COMPLETED, ClosingConditionStatus.WAIVED):
            completed += 1

    total = len(items)
    rate = (completed / total) if total > 0 else 0.0

    return ClosingChecklistSummary(
        total=total,
        by_category=by_category,
        by_status=by_status,
        completion_rate=round(rate, 3),
    )


@router.post("", response_model=ClosingChecklistOut, status_code=201)
async def create_closing_item(
    txn_id: uuid.UUID,
    body: ClosingChecklistCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    item = ClosingChecklist(transaction_id=txn_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.record(
        db, entity_type="ClosingChecklist", entity_id=item.id,
        action=AuditAction.CREATE, actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(item)
    return ClosingChecklistOut.model_validate(item)


@router.patch("/{item_id}", response_model=ClosingChecklistOut)
async def update_closing_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ClosingChecklistUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(ClosingChecklist).where(ClosingChecklist.id == item_id, ClosingChecklist.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클로징 항목을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    await audit_service.record(
        db, entity_type="ClosingChecklist", entity_id=item.id,
        action=AuditAction.UPDATE, actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(item)
    return ClosingChecklistOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_closing_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(ClosingChecklist).where(ClosingChecklist.id == item_id, ClosingChecklist.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클로징 항목을 찾을 수 없습니다")
    await audit_service.record(
        db, entity_type="ClosingChecklist", entity_id=item.id,
        action=AuditAction.DELETE, actor_email=claims.email,
    )
    await db.delete(item)
    await db.commit()
