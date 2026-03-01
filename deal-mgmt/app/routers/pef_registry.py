"""PEF 펀드 레지스트리 + FI 자동 추천 라우터."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims
from app.models.pef_fund_registry import PefFundRegistry
from app.schemas.pef_registry import FIRecommendation, PefFundOut
from app.services import transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PEF Registry"])


@router.get("/pef-registry", response_model=list[PefFundOut])
async def list_pef_funds(
    search: str | None = Query(None, description="GP명 또는 PEF명 검색"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
) -> list[PefFundOut]:
    """PEF 펀드 목록 조회 (페이지네이션, GP/PEF명 검색)."""
    q = select(PefFundRegistry)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            PefFundRegistry.pef_name.ilike(pattern)
            | PefFundRegistry.gp1.ilike(pattern)
            | PefFundRegistry.gp2.ilike(pattern)
            | PefFundRegistry.gp3.ilike(pattern)
        )
    q = q.order_by(PefFundRegistry.total_committed_capital.desc().nullslast()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [PefFundOut.model_validate(r) for r in result.scalars().all()]


@router.get("/pef-registry/count")
async def pef_fund_count(
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
) -> dict[str, int]:
    """PEF 펀드 총 건수."""
    q = select(func.count()).select_from(PefFundRegistry)
    total = (await db.execute(q)).scalar_one()
    return {"total": total}


@router.get(
    "/transactions/{txn_id}/fi-recommendations",
    response_model=list[FIRecommendation],
)
async def fi_recommendations(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[FIRecommendation]:
    """FI 자동 추천 — deal_value < total_committed_capital < deal_value * 5.

    GP별로 그룹핑하여 반환한다.
    """
    txn = await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    deal_value = getattr(txn, "estimated_deal_value", None)
    if deal_value is None:
        return []

    deal_value_dec = Decimal(str(deal_value))
    upper_bound = deal_value_dec * 5

    q = select(PefFundRegistry).where(
        PefFundRegistry.total_committed_capital > deal_value_dec,
        PefFundRegistry.total_committed_capital < upper_bound,
    )
    pefs = list((await db.execute(q)).scalars().all())

    # GP별 그룹핑 + 중복 제거
    gp_map: dict[str, list[PefFundRegistry]] = defaultdict(list)
    for pef in pefs:
        for gp in filter(None, [pef.gp1, pef.gp2, pef.gp3]):
            gp_name = gp.strip()
            if gp_name:
                gp_map[gp_name].append(pef)

    # 총약정액 합계 기준 정렬
    recommendations: list[FIRecommendation] = []
    for gp_name, funds in sorted(
        gp_map.items(),
        key=lambda x: sum(f.total_committed_capital or Decimal(0) for f in x[1]),
        reverse=True,
    ):
        # 펀드 중복 제거 (동일 GP가 여러 GP 슬롯에 있을 수 있음)
        seen_ids: set[uuid.UUID] = set()
        unique_funds: list[PefFundOut] = []
        for f in funds:
            if f.id not in seen_ids:
                seen_ids.add(f.id)
                unique_funds.append(PefFundOut.model_validate(f))

        total_sum = sum(f.total_committed_capital or Decimal(0) for f in unique_funds)
        recommendations.append(
            FIRecommendation(
                gp_name=gp_name,
                matching_funds=unique_funds,
                total_committed_sum=total_sum,
                fund_count=len(unique_funds),
            )
        )

    return recommendations
