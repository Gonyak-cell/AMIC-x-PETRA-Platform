"""PEF 펀드 레지스트리 + FI 자동 매핑 라우터.

FI 자동 매핑 알고리즘:
  1. 2021-01-01 이후 결성된 펀드만 대상
  2. 프로젝트 펀드(1회성 특수목적) 선택적 제외
  3. GP별 최소 펀드 약정총액을 기준값으로 산출
  4. target * 0.5 ≤ GP 기준값 ≤ target * 3 범위 매칭
  (단위: 억원)
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.pef_fund_registry import PefFundRegistry
from app.schemas.pef_registry import FIRecommendation, PefCountOut, PefFundOut
from app.services import transaction_service

if TYPE_CHECKING:
    from sqlalchemy import Select

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PEF Registry"])

_FI_DATE_CUTOFF = "2021-01-01"

# 프로젝트 펀드 제외 키워드 (실제 금감원 데이터에 따라 확장 가능)
_PROJECT_FUND_KEYWORDS = ["프로젝트"]


def _apply_search_filter(q: Select[Any], search: str) -> Select[Any]:
    """PEF 검색 필터를 쿼리에 적용한다."""
    escaped = search.replace("%", r"\%").replace("_", r"\_")
    pattern = f"%{escaped}%"
    return q.where(
        PefFundRegistry.pef_name.ilike(pattern, escape="\\")
        | PefFundRegistry.gp1.ilike(pattern, escape="\\")
        | PefFundRegistry.gp2.ilike(pattern, escape="\\")
        | PefFundRegistry.gp3.ilike(pattern, escape="\\")
    )


@router.get(
    "/pef-registry",
    response_model=list[PefFundOut],
    responses={
        403: {"description": "접근 권한 없음"},
        503: {"description": "DB 조회 실패"},
    },
)
async def list_pef_funds(
    search: str | None = Query(None, max_length=200, description="GP명 또는 PEF명 검색"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[PefFundOut]:
    """PEF 펀드 목록 조회 (페이지네이션, GP/PEF명 검색)."""
    if not claims.role or claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    q = select(PefFundRegistry)
    if search:
        q = _apply_search_filter(q, search)
    q = q.order_by(PefFundRegistry.total_committed_capital.desc().nullslast()).offset(skip).limit(limit)
    try:
        result = await db.execute(q)
    except SQLAlchemyError:
        logger.exception("PEF 목록 조회 실패: search=%s, skip=%d, limit=%d", search, skip, limit)
        raise HTTPException(status_code=503, detail="PEF 데이터 조회에 실패했습니다")
    rows = [PefFundOut.model_validate(r) for r in result.scalars().all()]
    logger.debug("PEF 목록 조회: search=%s, count=%d", search, len(rows))
    return rows


@router.get(
    "/pef-registry/count",
    response_model=PefCountOut,
    responses={
        403: {"description": "접근 권한 없음"},
        503: {"description": "DB 조회 실패"},
    },
)
async def pef_fund_count(
    search: str | None = Query(None, max_length=200, description="GP명 또는 PEF명 검색"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> PefCountOut:
    """PEF 펀드 총 건수 (검색 필터와 연동)."""
    if not claims.role or claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    q = select(func.count()).select_from(PefFundRegistry)
    if search:
        q = _apply_search_filter(q, search)
    try:
        total = (await db.execute(q)).scalar_one()
    except SQLAlchemyError:
        logger.exception("PEF 건수 조회 실패: search=%s", search)
        raise HTTPException(status_code=503, detail="PEF 데이터 조회에 실패했습니다")
    logger.debug("PEF 건수 조회: search=%s, total=%d", search, total)
    return PefCountOut(total=total)


def _format_billions(value: Decimal) -> str:
    """억원 단위 값을 읽기 쉬운 한국어 형태로 포맷팅한다."""
    if value >= 10000:
        return f"{value / Decimal('10000'):.1f}조"
    return f"{value:,.0f}억"


def _match_gps(
    pefs: list[PefFundRegistry],
    lower_bound: Decimal,
    upper_bound: Decimal,
) -> list[FIRecommendation]:
    """GP별 그룹핑 + min_fund_size 기반 범위 매칭.

    1. gp1/gp2/gp3 슬롯으로 GP별 펀드 그룹핑
    2. GP 내 펀드 중복 제거 (seen_ids)
    3. 유효 약정액(>0) 중 최솟값으로 범위 매칭
    4. min_fund_size 내림차순 정렬
    """
    gp_map: dict[str, list[PefFundRegistry]] = defaultdict(list)
    for pef in pefs:
        for gp in filter(None, [pef.gp1, pef.gp2, pef.gp3]):
            gp_name = gp.strip()
            if gp_name:
                gp_map[gp_name].append(pef)

    recommendations: list[FIRecommendation] = []
    for gp_name, funds in gp_map.items():
        seen_ids: set[uuid.UUID] = set()
        unique_raw: list[PefFundRegistry] = []
        unique_capitals: list[Decimal] = []
        for f in funds:
            if f.id not in seen_ids:
                seen_ids.add(f.id)
                unique_raw.append(f)
                if f.total_committed_capital and f.total_committed_capital > 0:
                    unique_capitals.append(f.total_committed_capital)

        if not unique_capitals:
            continue

        min_size = min(unique_capitals)
        if not (lower_bound <= min_size <= upper_bound):
            continue

        total_sum = sum(unique_capitals)
        match_reason = (
            f"최소 펀드 약정총액 {_format_billions(min_size)} (2021년 이후 결성, 펀드 {len(unique_capitals)}건)"
        )

        recommendations.append(
            FIRecommendation(
                gp_name=gp_name,
                min_fund_size=min_size,
                matching_funds=[PefFundOut.model_validate(f) for f in unique_raw],
                total_committed_sum=total_sum,
                fund_count=len(unique_capitals),
                match_reason=match_reason,
            )
        )

    recommendations.sort(key=lambda r: r.min_fund_size, reverse=True)
    return recommendations


@router.get(
    "/transactions/{txn_id}/fi-recommendations",
    response_model=list[FIRecommendation],
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "거래를 찾을 수 없음"},
        422: {"description": "거래금액 미설정 또는 유효하지 않은 파라미터"},
        503: {"description": "DB 조회 실패"},
    },
)
async def fi_recommendations(
    txn_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200, description="반환할 GP 추천 최대 건수"),
    exclude_project_funds: bool = Query(True, description="프로젝트 펀드 제외 여부"),
    lower_multiplier: Decimal = Query(
        Decimal("0.5"),
        ge=Decimal("0.1"),
        le=Decimal("1.0"),
        description="하한 배수 (target × lower)",
    ),
    upper_multiplier: Decimal = Query(
        Decimal("3.0"),
        ge=Decimal("1.0"),
        le=Decimal("5.0"),
        description="상한 배수 (target × upper)",
    ),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[FIRecommendation]:
    """FI 자동 매핑 — GP의 최소 펀드 약정총액 기준 범위 매칭.

    2021년 이후 결성 펀드를 GP별로 그룹핑한 뒤,
    GP의 최소 펀드 약정총액이 target × lower ~ target × upper 범위인
    GP만 추천한다. (단위: 억원)
    """
    # ── CLIENT 접근 차단 (list/count와 동일 정책) ──────────────
    if not claims.role or claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")

    # ── 입력 검증 ──────────────────────────────────────────────
    if lower_multiplier > upper_multiplier:
        logger.warning("배수 역전: lower=%s > upper=%s", lower_multiplier, upper_multiplier)
        raise HTTPException(
            status_code=422,
            detail="하한 배수(lower_multiplier)가 상한 배수(upper_multiplier)보다 클 수 없습니다",
        )

    try:
        txn = await transaction_service.get_transaction(db, txn_id)
    except SQLAlchemyError:
        logger.exception("트랜잭션 조회 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="거래 데이터 조회에 실패했습니다")

    if txn.estimated_deal_value is None:
        raise HTTPException(
            status_code=422,
            detail="거래금액(estimated_deal_value)이 설정되지 않았습니다. 거래 설정에서 예상 거래금액을 입력해 주세요.",
        )

    try:
        target_amount = Decimal(str(txn.estimated_deal_value))
    except (InvalidOperation, ValueError):
        logger.warning("거래금액 Decimal 변환 실패: txn_id=%s, deal_value=%r", txn_id, txn.estimated_deal_value)
        raise HTTPException(status_code=422, detail="거래금액을 숫자로 변환할 수 없습니다")

    if target_amount <= 0:
        logger.info("거래금액 0 이하 — 추천 생략: txn_id=%s, deal_value=%s", txn_id, target_amount)
        return []

    lower_bound = target_amount * lower_multiplier
    upper_bound = target_amount * upper_multiplier

    # ── DB 조회: 날짜 필터 + 프로젝트 펀드 제외 ────────────────
    q = select(PefFundRegistry).where(
        PefFundRegistry.registration_date.isnot(None),
        PefFundRegistry.registration_date >= _FI_DATE_CUTOFF,
        PefFundRegistry.total_committed_capital.isnot(None),
        PefFundRegistry.total_committed_capital > 0,
    )

    if exclude_project_funds:
        for keyword in _PROJECT_FUND_KEYWORDS:
            q = q.where(~PefFundRegistry.pef_name.ilike(f"%{keyword}%", escape="\\"))
        if txn.target_company_name and len(txn.target_company_name) >= 2:
            escaped_name = txn.target_company_name.replace("%", r"\%").replace("_", r"\_")
            q = q.where(~PefFundRegistry.pef_name.ilike(f"%{escaped_name}%", escape="\\"))

    try:
        pefs = list((await db.execute(q)).scalars().all())
    except SQLAlchemyError:
        logger.exception("FI 추천 DB 조회 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="추천 데이터 조회에 실패했습니다")

    # ── GP 매칭 알고리즘 ───────────────────────────────────────
    results = _match_gps(pefs, lower_bound, upper_bound)[:limit]

    logger.info(
        "FI 추천 완료: txn_id=%s, target=%s억, matched_gps=%d, total_funds=%d",
        txn_id,
        target_amount,
        len(results),
        sum(r.fund_count for r in results),
    )
    return results
