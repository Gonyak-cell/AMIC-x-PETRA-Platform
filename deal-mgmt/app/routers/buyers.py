"""매수자 후보 파이프라인 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction
from app.schemas.buyer import (
    BuyerCandidateCreate,
    BuyerCandidateOut,
    BuyerCandidateUpdate,
    BuyerPipelineSummary,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/buyers", tags=["Buyers"])


@router.get("", response_model=list[BuyerCandidateOut])
async def list_buyers(
    txn_id: uuid.UUID,
    buyer_status: str | None = Query(None, alias="status"),
    buyer_type: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id)
    if buyer_status:
        q = q.where(BuyerCandidate.status == buyer_status)
    if buyer_type:
        q = q.where(BuyerCandidate.buyer_type == buyer_type)
    q = q.order_by(BuyerCandidate.created_at.desc())
    result = await db.execute(q)
    return [BuyerCandidateOut.model_validate(b) for b in result.scalars().all()]


@router.get("/summary", response_model=BuyerPipelineSummary)
async def buyer_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    """매수자 파이프라인 요약 통계."""
    await transaction_service.get_transaction(db, txn_id)
    q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id)
    result = await db.execute(q)
    buyers = list(result.scalars().all())

    by_status: dict[str, int] = {}
    ioi_values: list[float] = []
    loi_values: list[float] = []
    for b in buyers:
        by_status[b.status.value] = by_status.get(b.status.value, 0) + 1
        if b.ioi_value:
            ioi_values.append(float(b.ioi_value))
        if b.loi_value:
            loi_values.append(float(b.loi_value))

    return BuyerPipelineSummary(
        total=len(buyers),
        by_status=by_status,
        avg_ioi_value=sum(ioi_values) / len(ioi_values) if ioi_values else None,
        avg_loi_value=sum(loi_values) / len(loi_values) if loi_values else None,
    )


@router.post("", response_model=BuyerCandidateOut, status_code=201)
async def add_buyer(
    txn_id: uuid.UUID,
    body: BuyerCandidateCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    buyer = BuyerCandidate(transaction_id=txn_id, **body.model_dump())
    db.add(buyer)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(),
    )
    await db.commit()
    await db.refresh(buyer)
    return BuyerCandidateOut.model_validate(buyer)


@router.get("/{buyer_id}", response_model=BuyerCandidateOut)
async def get_buyer(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(BuyerCandidate).where(BuyerCandidate.id == buyer_id, BuyerCandidate.transaction_id == txn_id)
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="매수자 후보를 찾을 수 없습니다")
    return BuyerCandidateOut.model_validate(buyer)


@router.patch("/{buyer_id}", response_model=BuyerCandidateOut)
async def update_buyer(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    body: BuyerCandidateUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(BuyerCandidate).where(BuyerCandidate.id == buyer_id, BuyerCandidate.transaction_id == txn_id)
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="매수자 후보를 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(buyer, k) for k in update_data}
    for k, v in update_data.items():
        setattr(buyer, k, v)
    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value={k: str(v) if v is not None else None for k, v in old_value.items()},
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(buyer)
    return BuyerCandidateOut.model_validate(buyer)


@router.delete("/{buyer_id}", status_code=204)
async def remove_buyer(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(BuyerCandidate).where(BuyerCandidate.id == buyer_id, BuyerCandidate.transaction_id == txn_id)
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="매수자 후보를 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(buyer)
    await db.commit()
