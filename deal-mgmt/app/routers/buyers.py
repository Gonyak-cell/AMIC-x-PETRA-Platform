"""매수자 후보 파이프라인 라우터."""

from __future__ import annotations

import logging
import uuid
from decimal import ROUND_HALF_UP, Decimal

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
    BuyerCandidateListResponse,
    BuyerCandidateOut,
    BuyerCandidateUpdate,
    BuyerPipelineSummary,
)
from app.services import audit_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}/buyers", tags=["Buyers"])

_SHORT_LIST_TIERS = frozenset({BuyerTier.TIER_1, BuyerTier.TIER_2, BuyerTier.TIER_3})


def _sync_tier_short_list(data: dict[str, object]) -> None:
    """Tier 값에 따라 is_short_listed를 동기화한다 (SSOT).

    tier + is_short_listed가 동시에 전달되더라도 tier가 우선한다.
    tier가 없으면 is_short_listed 직접 PATCH를 허용한다.
    """
    tier = data.get("tier")
    if tier is not None or "tier" in data:
        data["is_short_listed"] = tier in _SHORT_LIST_TIERS


# ── BuyerCandidateStatus 상태 전이 규칙 ──────────────────
# M&A 파이프라인 기반: 선형 진행 + REJECTED 분기 + BID 분기
# 종단 상태(SELECTED, REJECTED, BID_DROPPED)에서는 전이 불가
_S = BuyerCandidateStatus
_BUYER_STATUS_TRANSITIONS: dict[BuyerCandidateStatus, set[BuyerCandidateStatus]] = {
    _S.IDENTIFIED: {_S.CONTACTED, _S.BID_DROPPED, _S.REJECTED},
    _S.CONTACTED: {_S.NDA_SENT, _S.NDA_SIGNED, _S.BID_DROPPED, _S.REJECTED},
    _S.NDA_SENT: {_S.NDA_SIGNED, _S.BID_DROPPED, _S.REJECTED},
    _S.NDA_SIGNED: {_S.CIM_SENT, _S.BID_DROPPED, _S.REJECTED},
    _S.CIM_SENT: {_S.INTEREST_CONFIRMED, _S.BID_DROPPED, _S.REJECTED},
    _S.INTEREST_CONFIRMED: {_S.IOI_RECEIVED, _S.BID_NOT_SUBMITTED, _S.BID_DROPPED, _S.REJECTED},
    _S.IOI_RECEIVED: {_S.IOI_ACCEPTED, _S.BID_DROPPED, _S.REJECTED},
    _S.IOI_ACCEPTED: {_S.DD_GRANTED, _S.BID_SUBMITTED, _S.BID_DROPPED, _S.REJECTED},
    _S.DD_GRANTED: {_S.DD_IN_PROGRESS, _S.BID_DROPPED, _S.REJECTED},
    _S.DD_IN_PROGRESS: {_S.LOI_RECEIVED, _S.BID_SUBMITTED, _S.BID_DROPPED, _S.REJECTED},
    _S.LOI_RECEIVED: {_S.LOI_ACCEPTED, _S.BID_DROPPED, _S.REJECTED},
    _S.LOI_ACCEPTED: {_S.SELECTED, _S.BID_DROPPED, _S.REJECTED},
    _S.SELECTED: set(),
    _S.REJECTED: set(),
    _S.BID_SUBMITTED: {_S.SELECTED, _S.BID_DROPPED, _S.REJECTED},
    _S.BID_NOT_SUBMITTED: {_S.BID_SUBMITTED, _S.BID_DROPPED, _S.REJECTED},
    _S.BID_DROPPED: set(),
}


@router.get("", response_model=BuyerCandidateListResponse)
async def list_buyers(
    txn_id: uuid.UUID,
    buyer_status: BuyerCandidateStatus | None = Query(None, alias="status"),
    buyer_type: BuyerType | None = Query(None, alias="type"),
    tier: BuyerTier | None = Query(None),
    is_short_listed: bool | None = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> BuyerCandidateListResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    base = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id)
    if buyer_status:
        base = base.where(BuyerCandidate.status == buyer_status)
    if buyer_type:
        base = base.where(BuyerCandidate.buyer_type == buyer_type)
    if tier:
        base = base.where(BuyerCandidate.tier == tier)
    if is_short_listed is not None:
        base = base.where(BuyerCandidate.is_short_listed == is_short_listed)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = base.order_by(BuyerCandidate.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    items = [BuyerCandidateOut.model_validate(b) for b in result.scalars().all()]
    return BuyerCandidateListResponse(items=items, total=total, limit=limit, offset=offset)


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
    avg_ioi = (
        Decimal(str(agg_row.avg_ioi)).quantize(_q2, rounding=ROUND_HALF_UP) if agg_row.avg_ioi is not None else None
    )
    avg_loi = (
        Decimal(str(agg_row.avg_loi)).quantize(_q2, rounding=ROUND_HALF_UP) if agg_row.avg_loi is not None else None
    )

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
    data = body.model_dump()
    _sync_tier_short_list(data)

    buyer = BuyerCandidate(transaction_id=txn_id, **data)
    db.add(buyer)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=data,
    )
    await db.commit()
    await db.refresh(buyer)
    return BuyerCandidateOut.model_validate(buyer)


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
    await transaction_service.get_transaction(db, txn_id)
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
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(BuyerCandidate).where(BuyerCandidate.id == buyer_id, BuyerCandidate.transaction_id == txn_id)
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="매수자 후보를 찾을 수 없습니다")

    update_data = body.model_dump(exclude_unset=True)

    # 상태 전이 검증
    if "status" in update_data:
        new_status = update_data["status"]
        allowed = _BUYER_STATUS_TRANSITIONS.get(buyer.status, set())
        if new_status not in allowed:
            logger.warning(
                "상태 전이 거부: buyer=%s, %s → %s, actor=%s",
                buyer_id,
                buyer.status.value,
                new_status.value,
                claims.email,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="상태 전이 불가: 현재 상태에서 요청한 상태로 전환할 수 없습니다",
            )

    _sync_tier_short_list(update_data)
    if "tier" in update_data:
        logger.debug(
            "Tier 동기화: buyer=%s, tier=%s → is_short_listed=%s",
            buyer_id,
            update_data.get("tier"),
            update_data.get("is_short_listed"),
        )

    old_value = {k: getattr(buyer, k, None) for k in update_data}
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
    await transaction_service.get_transaction(db, txn_id)
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
            "contact_name": (buyer.contact_name[0] + "***") if buyer.contact_name else None,
            "corp_code": buyer.corp_code,
        },
        notes=cascade_notes,
    )
    await db.delete(buyer)
    await db.commit()
