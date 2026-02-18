"""IOI/LOI/최종제안 관리 + 비교 매트릭스 라우터."""

from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, BidType
from app.schemas.bid import BidComparisonItem, BidCreate, BidOut, BidUpdate
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/bids", tags=["Bids"])


@router.get("", response_model=list[BidOut])
async def list_bids(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID | None = None,
    bid_type: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(Bid).where(Bid.transaction_id == txn_id)
    if buyer_id:
        q = q.where(Bid.buyer_candidate_id == buyer_id)
    if bid_type:
        q = q.where(Bid.bid_type == bid_type)
    q = q.order_by(Bid.created_at.desc())
    result = await db.execute(q)
    return [BidOut.model_validate(b) for b in result.scalars().all()]


@router.get("/comparison", response_model=list[BidComparisonItem])
async def bid_comparison_matrix(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    """매수자별 IOI/LOI/최종제안 비교 매트릭스."""
    await transaction_service.get_transaction(db, txn_id)

    # 모든 매수자
    buyers_q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id)
    buyers = list((await db.execute(buyers_q)).scalars().all())

    # 모든 Bid
    bids_q = select(Bid).where(Bid.transaction_id == txn_id).order_by(Bid.created_at.desc())
    bids = list((await db.execute(bids_q)).scalars().all())

    # 매수자별 최신 Bid 그룹화
    buyer_bids: dict[uuid.UUID, dict[str, Bid]] = defaultdict(dict)
    for bid in bids:
        bt = bid.bid_type.value
        if bt not in buyer_bids[bid.buyer_candidate_id]:
            buyer_bids[bid.buyer_candidate_id][bt] = bid

    result = []
    for buyer in buyers:
        bids_map = buyer_bids.get(buyer.id, {})
        result.append(BidComparisonItem(
            buyer_id=buyer.id,
            buyer_name=buyer.company_name,
            buyer_type=buyer.buyer_type.value,
            ioi=BidOut.model_validate(bids_map["IOI"]) if "IOI" in bids_map else None,
            loi=BidOut.model_validate(bids_map["LOI"]) if "LOI" in bids_map else None,
            final_offer=BidOut.model_validate(bids_map["FINAL_OFFER"]) if "FINAL_OFFER" in bids_map else None,
        ))

    return result


@router.post("", response_model=BidOut, status_code=201)
async def create_bid(
    txn_id: uuid.UUID,
    body: BidCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    bid = Bid(transaction_id=txn_id, **body.model_dump())
    db.add(bid)
    await db.flush()
    await audit_service.record(
        db, entity_type="Bid", entity_id=bid.id,
        action=AuditAction.CREATE, actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(bid)
    return BidOut.model_validate(bid)


@router.patch("/{bid_id}", response_model=BidOut)
async def update_bid(
    txn_id: uuid.UUID,
    bid_id: uuid.UUID,
    body: BidUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(Bid).where(Bid.id == bid_id, Bid.transaction_id == txn_id)
    bid = (await db.execute(q)).scalar_one_or_none()
    if bid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="입찰을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(bid, k, v)
    await audit_service.record(
        db, entity_type="Bid", entity_id=bid.id,
        action=AuditAction.UPDATE, actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(bid)
    return BidOut.model_validate(bid)


@router.delete("/{bid_id}", status_code=204)
async def delete_bid(
    txn_id: uuid.UUID,
    bid_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(Bid).where(Bid.id == bid_id, Bid.transaction_id == txn_id)
    bid = (await db.execute(q)).scalar_one_or_none()
    if bid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="입찰을 찾을 수 없습니다")
    await audit_service.record(
        db, entity_type="Bid", entity_id=bid.id,
        action=AuditAction.DELETE, actor_email=claims.email,
    )
    await db.delete(bid)
    await db.commit()
