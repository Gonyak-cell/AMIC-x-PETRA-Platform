"""Closing 체크리스트 관리 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.closing_checklist import ClosingChecklist
from app.models.enums import AuditAction, ClosingConditionStatus
from app.schemas.closing import (
    ClosingChecklistCreate,
    ClosingChecklistOut,
    ClosingChecklistSummary,
    ClosingChecklistUpdate,
)
from app.services import audit_service, transaction_service
from app.services.transaction_service import _STANDARD_CLOSING_ITEMS

router = APIRouter(prefix="/transactions/{txn_id}/closing", tags=["Closing"])


@router.get("", response_model=list[ClosingChecklistOut])
async def list_closing_items(
    txn_id: uuid.UUID,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
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
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
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
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    item = ClosingChecklist(transaction_id=txn_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="ClosingChecklist",
        entity_id=item.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
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
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(ClosingChecklist).where(ClosingChecklist.id == item_id, ClosingChecklist.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Closing 항목을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(item, k) for k in update_data}
    for k, v in update_data.items():
        setattr(item, k, v)
    await audit_service.record(
        db,
        entity_type="ClosingChecklist",
        entity_id=item.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(item)
    return ClosingChecklistOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_closing_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(ClosingChecklist).where(ClosingChecklist.id == item_id, ClosingChecklist.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Closing 항목을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="ClosingChecklist",
        entity_id=item.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(item)
    await db.commit()


@router.post("/init-standard", response_model=list[ClosingChecklistOut], status_code=201)
async def init_standard_checklist(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """기존 거래에 표준 Closing 체크리스트를 초기화한다.

    항목이 이미 존재하는 경우 재실행하지 않는다 (멱등).
    """
    await transaction_service.get_transaction(db, txn_id)

    existing = (
        await db.execute(select(ClosingChecklist).where(ClosingChecklist.transaction_id == txn_id).limit(1))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closing 체크리스트가 이미 초기화되어 있습니다. 항목을 직접 추가하세요.",
        )

    items: list[ClosingChecklist] = []
    for item_data in _STANDARD_CLOSING_ITEMS:
        item = ClosingChecklist(transaction_id=txn_id, **item_data)
        db.add(item)
        items.append(item)

    await audit_service.record(
        db,
        entity_type="ClosingChecklist",
        entity_id=txn_id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"action": "init_standard", "count": len(items)},
    )
    await db.commit()
    for item in items:
        await db.refresh(item)
    return [ClosingChecklistOut.model_validate(i) for i in items]
