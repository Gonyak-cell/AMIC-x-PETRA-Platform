"""어닝아웃 마일스톤 관리 라우터."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.earnout import EarnoutMilestone
from app.models.enums import AuditAction
from app.schemas.earnout import EarnoutCreate, EarnoutOut, EarnoutSummary, EarnoutUpdate
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/earnout", tags=["Earnout"])


@router.get("", response_model=list[EarnoutOut])
async def list_earnout_milestones(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = (
        select(EarnoutMilestone)
        .where(EarnoutMilestone.transaction_id == txn_id)
        .order_by(EarnoutMilestone.measurement_start, EarnoutMilestone.created_at.desc())
    )
    result = await db.execute(q)
    return [EarnoutOut.model_validate(m) for m in result.scalars().all()]


@router.get("/summary", response_model=EarnoutSummary)
async def earnout_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(EarnoutMilestone).where(EarnoutMilestone.transaction_id == txn_id)
    result = await db.execute(q)
    items = list(result.scalars().all())

    by_status: dict[str, int] = {}
    total_target = Decimal("0")
    total_actual = Decimal("0")
    total_payment = Decimal("0")
    for item in items:
        by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
        total_target += item.target_value or Decimal("0")
        total_actual += item.actual_value or Decimal("0")
        total_payment += item.payment_amount or Decimal("0")

    return EarnoutSummary(
        total=len(items),
        total_target=total_target,
        total_actual=total_actual,
        total_payment=total_payment,
        by_status=by_status,
    )


@router.post("", response_model=EarnoutOut, status_code=201)
async def create_earnout(
    txn_id: uuid.UUID,
    body: EarnoutCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    milestone = EarnoutMilestone(transaction_id=txn_id, **body.model_dump())
    db.add(milestone)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="EarnoutMilestone",
        entity_id=milestone.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(milestone)
    return EarnoutOut.model_validate(milestone)


@router.patch("/{milestone_id}", response_model=EarnoutOut)
async def update_earnout(
    txn_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: EarnoutUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(EarnoutMilestone).where(EarnoutMilestone.id == milestone_id, EarnoutMilestone.transaction_id == txn_id)
    milestone = (await db.execute(q)).scalar_one_or_none()
    if milestone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="어닝아웃 마일스톤을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(milestone, k, v)
    await audit_service.record(
        db,
        entity_type="EarnoutMilestone",
        entity_id=milestone.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(milestone)
    return EarnoutOut.model_validate(milestone)


@router.delete("/{milestone_id}", status_code=204)
async def delete_earnout(
    txn_id: uuid.UUID,
    milestone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(EarnoutMilestone).where(EarnoutMilestone.id == milestone_id, EarnoutMilestone.transaction_id == txn_id)
    milestone = (await db.execute(q)).scalar_one_or_none()
    if milestone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="어닝아웃 마일스톤을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="EarnoutMilestone",
        entity_id=milestone.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(milestone)
    await db.commit()
