"""매수자 후보 파이프라인 라우터."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.buyer_candidate import BuyerCandidate
from app.models.buyer_marketing_log import BuyerMarketingLog
from app.models.consortium_mapping import ConsortiumMapping
from app.models.enums import AuditAction, BuyerCandidateStatus, BuyerTier, BuyerType
from app.schemas.buyer import (
    BiddingSummary,
    BuyerCandidateCreate,
    BuyerCandidateOut,
    BuyerCandidateUpdate,
    BuyerPipelineSummary,
    ShortListPromoteRequest,
)
from app.services import audit_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}/buyers", tags=["Buyers"])


@router.get("", response_model=list[BuyerCandidateOut])
async def list_buyers(
    txn_id: uuid.UUID,
    buyer_status: BuyerCandidateStatus | None = Query(None, alias="status"),
    buyer_type: BuyerType | None = Query(None, alias="type"),
    tier: BuyerTier | None = Query(None),
    is_short_listed: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[BuyerCandidateOut]:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id)
    if buyer_status:
        q = q.where(BuyerCandidate.status == buyer_status)
    if buyer_type:
        q = q.where(BuyerCandidate.buyer_type == buyer_type)
    if tier:
        q = q.where(BuyerCandidate.tier == tier)
    if is_short_listed is not None:
        q = q.where(BuyerCandidate.is_short_listed == is_short_listed)
    q = q.order_by(BuyerCandidate.created_at.desc())
    result = await db.execute(q)
    return [BuyerCandidateOut.model_validate(b) for b in result.scalars().all()]


@router.get("/summary", response_model=BuyerPipelineSummary)
async def buyer_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> BuyerPipelineSummary:
    """매수자 파이프라인 요약 통계 — DB 집계 쿼리로 처리."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    _where = BuyerCandidate.transaction_id == txn_id

    # 1. 전체 카운트 + 평균 (nullif로 0 제외 — 기존 동작 유지)
    agg_q = (
        select(
            func.count().label("total"),
            func.avg(func.nullif(BuyerCandidate.ioi_value, 0)).label("avg_ioi"),
            func.avg(func.nullif(BuyerCandidate.loi_value, 0)).label("avg_loi"),
        )
        .select_from(BuyerCandidate)
        .where(_where)
    )
    agg_row = (await db.execute(agg_q)).one()

    # 2. 상태별 카운트
    status_q = select(BuyerCandidate.status, func.count().label("cnt")).where(_where).group_by(BuyerCandidate.status)
    by_status = {row.status.value: row.cnt for row in (await db.execute(status_q)).all()}

    # 3. 티어별 카운트
    tier_q = (
        select(BuyerCandidate.tier, func.count().label("cnt"))
        .where(_where, BuyerCandidate.tier.isnot(None))
        .group_by(BuyerCandidate.tier)
    )
    by_tier = {row.tier.value: row.cnt for row in (await db.execute(tier_q)).all()}

    # SQLite AVG는 float 반환 — Decimal(20,2) 정밀도 보장
    _q2 = Decimal("0.01")
    avg_ioi = Decimal(str(agg_row.avg_ioi)).quantize(_q2) if agg_row.avg_ioi is not None else None
    avg_loi = Decimal(str(agg_row.avg_loi)).quantize(_q2) if agg_row.avg_loi is not None else None

    return BuyerPipelineSummary(
        total=agg_row.total,
        by_status=by_status,
        by_tier=by_tier,
        avg_ioi_value=avg_ioi,
        avg_loi_value=avg_loi,
    )


@router.post("", response_model=BuyerCandidateOut, status_code=201)
async def add_buyer(
    txn_id: uuid.UUID,
    body: BuyerCandidateCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> BuyerCandidateOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    buyer = BuyerCandidate(transaction_id=txn_id, **body.model_dump())
    db.add(buyer)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(buyer)
    return BuyerCandidateOut.model_validate(buyer)


@router.post("/promote-short-list", response_model=list[BuyerCandidateOut])
async def promote_short_list(
    txn_id: uuid.UUID,
    body: ShortListPromoteRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> list[BuyerCandidateOut]:
    """체크된 매수자들을 Short-List로 승격한다.

    contact_name, contact_email, contact_phone 중 하나라도 없으면 422.
    """
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    q = select(BuyerCandidate).where(
        BuyerCandidate.transaction_id == txn_id,
        BuyerCandidate.id.in_(body.buyer_ids),
    )
    buyers_list = list((await db.execute(q)).scalars().all())

    if len(buyers_list) != len(body.buyer_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일부 매수자 후보를 찾을 수 없습니다",
        )

    # 연락처 필수 검증
    missing: list[dict] = []
    for b in buyers_list:
        lacks = []
        if not b.contact_name:
            lacks.append("contact_name")
        if not b.contact_email:
            lacks.append("contact_email")
        if not b.contact_phone:
            lacks.append("contact_phone")
        if lacks:
            missing.append({"buyer_id": str(b.id), "company_name": b.company_name, "missing_fields": lacks})

    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Short-List 승격을 위해 연락처 정보가 필요합니다", "missing_contact": missing},
        )

    for b in buyers_list:
        b.is_short_listed = True
        await audit_service.record(
            db,
            entity_type="BuyerCandidate",
            entity_id=b.id,
            action=AuditAction.UPDATE,
            actor_email=claims.email,
            old_value={"is_short_listed": False},
            new_value={"is_short_listed": True},
            notes="Short-List 승격",
        )

    await db.commit()
    for b in buyers_list:
        await db.refresh(b)
    return [BuyerCandidateOut.model_validate(b) for b in buyers_list]


@router.get("/bidding-summary", response_model=BiddingSummary)
async def bidding_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> BiddingSummary:
    """입찰 결과 집계 — BID_SUBMITTED / BID_NOT_SUBMITTED / BID_DROPPED 건수."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    _where = BuyerCandidate.transaction_id == txn_id

    bid_statuses = [
        BuyerCandidateStatus.BID_SUBMITTED,
        BuyerCandidateStatus.BID_NOT_SUBMITTED,
        BuyerCandidateStatus.BID_DROPPED,
    ]

    q = (
        select(BuyerCandidate.status, func.count().label("cnt"))
        .where(_where, BuyerCandidate.status.in_(bid_statuses))
        .group_by(BuyerCandidate.status)
    )
    rows = (await db.execute(q)).all()
    counts = {row.status.value: row.cnt for row in rows}

    return BiddingSummary(
        total_bidders=sum(counts.values()),
        bid_submitted=counts.get("BID_SUBMITTED", 0),
        bid_not_submitted=counts.get("BID_NOT_SUBMITTED", 0),
        bid_dropped=counts.get("BID_DROPPED", 0),
    )


@router.get("/{buyer_id}", response_model=BuyerCandidateOut)
async def get_buyer(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> BuyerCandidateOut:
    await check_client_deal_access(db, txn_id, claims)
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
    claims: JWTClaims = Depends(require_write_access()),
) -> BuyerCandidateOut:
    await check_client_deal_access(db, txn_id, claims)
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
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(buyer)
    return BuyerCandidateOut.model_validate(buyer)


@router.delete("/{buyer_id}", status_code=204)
async def remove_buyer(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await check_client_deal_access(db, txn_id, claims)
    q = select(BuyerCandidate).where(BuyerCandidate.id == buyer_id, BuyerCandidate.transaction_id == txn_id)
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="매수자 후보를 찾을 수 없습니다")

    # CASCADE 삭제 대상 카운트 (감사 추적)
    log_count = (
        await db.execute(
            select(func.count()).select_from(BuyerMarketingLog).where(BuyerMarketingLog.buyer_id == buyer_id)
        )
    ).scalar_one()
    consortium_count = (
        await db.execute(
            select(func.count())
            .select_from(ConsortiumMapping)
            .where((ConsortiumMapping.lead_buyer_id == buyer_id) | (ConsortiumMapping.co_investor_buyer_id == buyer_id))
        )
    ).scalar_one()

    cascade_notes = f"CASCADE 삭제: 마케팅 로그 {log_count}건, 컨소시엄 매핑 {consortium_count}건"
    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
        old_value={
            "company_name": buyer.company_name,
            "tier": buyer.tier,
            "status": buyer.status,
            "buyer_type": buyer.buyer_type,
            "deal_role": buyer.deal_role,
            "contact_name": buyer.contact_name,
            "corp_code": buyer.corp_code,
        },
        notes=cascade_notes,
    )
    await db.delete(buyer)
    await db.commit()
