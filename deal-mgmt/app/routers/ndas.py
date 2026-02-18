"""NDA 관리 라우터 — 매수자별 NDA 추적."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.enums import AuditAction, NdaStatus
from app.models.nda import NDA
from app.schemas.nda import NDACreate, NDAOut, NDASummary, NDAUpdate
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/ndas", tags=["NDAs"])


@router.get("", response_model=list[NDAOut])
async def list_ndas(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(NDA).where(NDA.transaction_id == txn_id)
    if buyer_id:
        q = q.where(NDA.buyer_candidate_id == buyer_id)
    q = q.order_by(NDA.created_at.desc())
    result = await db.execute(q)
    return [NDAOut.model_validate(n) for n in result.scalars().all()]


@router.get("/summary", response_model=NDASummary)
async def nda_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(NDA).where(NDA.transaction_id == txn_id)
    result = await db.execute(q)
    ndas = list(result.scalars().all())

    by_status: dict[str, int] = {}
    signed = 0
    pending = 0
    for n in ndas:
        by_status[n.status.value] = by_status.get(n.status.value, 0) + 1
        if n.status == NdaStatus.SIGNED:
            signed += 1
        elif n.status in (NdaStatus.DRAFT, NdaStatus.SENT):
            pending += 1

    return NDASummary(total=len(ndas), by_status=by_status, signed_count=signed, pending_count=pending)


@router.post("", response_model=NDAOut, status_code=201)
async def create_nda(
    txn_id: uuid.UUID,
    body: NDACreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    nda = NDA(transaction_id=txn_id, **body.model_dump())
    db.add(nda)
    await db.flush()
    await audit_service.record(
        db, entity_type="NDA", entity_id=nda.id,
        action=AuditAction.CREATE, actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(nda)
    return NDAOut.model_validate(nda)


@router.patch("/{nda_id}", response_model=NDAOut)
async def update_nda(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    body: NDAUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(NDA).where(NDA.id == nda_id, NDA.transaction_id == txn_id)
    nda = (await db.execute(q)).scalar_one_or_none()
    if nda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NDA를 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(nda, k, v)
    await audit_service.record(
        db, entity_type="NDA", entity_id=nda.id,
        action=AuditAction.UPDATE, actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(nda)
    return NDAOut.model_validate(nda)


@router.delete("/{nda_id}", status_code=204)
async def delete_nda(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(NDA).where(NDA.id == nda_id, NDA.transaction_id == txn_id)
    nda = (await db.execute(q)).scalar_one_or_none()
    if nda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NDA를 찾을 수 없습니다")
    await audit_service.record(
        db, entity_type="NDA", entity_id=nda.id,
        action=AuditAction.DELETE, actor_email=claims.email,
    )
    await db.delete(nda)
    await db.commit()
