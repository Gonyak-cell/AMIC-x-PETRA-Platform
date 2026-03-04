"""PEF 펀드 레지스트리 + FI 자동 매핑 라우터.

FI 자동 매핑 알고리즘 (v2 — GP 프로필 Tier 분류):
  1. 2021-01-01 이후 결성된 펀드만 대상
  2. 프로젝트 펀드(1회성 특수목적) 선택적 제외
  3. GP별 최소 펀드 약정총액을 기준값으로 산출
  4. target * lower ≤ GP 기준값 ≤ target * upper 범위 매칭
  5. GP 프로필 기반 Tier 1/2 분류 (최소기준점 + 키워드)
  (단위: 억원)
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limiter import fi_rate_limiter
from app.core.security import JWTClaims, require_role
from app.models.enums import AuditAction
from app.models.pef_fund_registry import PefFundRegistry
from app.schemas.pef_registry import FIRecommendationV2, PefCountOut, PefFundOut
from app.services import audit_service, fi_mapping_service, transaction_service

if TYPE_CHECKING:
    from sqlalchemy import Select

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PEF Registry"])

_FI_DATE_CUTOFF = "2021-01-01"

# 프로젝트 펀드 제외 키워드 (실제 금감원 데이터에 따라 확장 가능)
_PROJECT_FUND_KEYWORDS = ["프로젝트"]

# RBAC — 읽기: ADMIN, MANAGER, ANALYST (CLIENT 제외)
_READ_ACCESS = require_role("ADMIN", "MANAGER", "ANALYST")


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
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> list[PefFundOut]:
    """PEF 펀드 목록 조회 (페이지네이션, GP/PEF명 검색)."""
    safe_search = search.replace("\n", "").replace("\r", "") if search else search
    q = select(PefFundRegistry)
    if safe_search:
        q = _apply_search_filter(q, safe_search)
    q = q.order_by(PefFundRegistry.total_committed_capital.desc().nullslast()).offset(skip).limit(limit)
    try:
        result = await db.execute(q)
    except SQLAlchemyError:
        logger.exception("PEF 목록 조회 실패: search=%s, skip=%d, limit=%d", safe_search, skip, limit)
        raise HTTPException(status_code=503, detail="PEF 데이터 조회에 실패했습니다")
    rows = [PefFundOut.model_validate(r) for r in result.scalars().all()]
    logger.debug("PEF 목록 조회: search=%s, count=%d", safe_search, len(rows))
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
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> PefCountOut:
    """PEF 펀드 총 건수 (검색 필터와 연동)."""
    safe_search = search.replace("\n", "").replace("\r", "") if search else search
    q = select(func.count()).select_from(PefFundRegistry)
    if safe_search:
        q = _apply_search_filter(q, safe_search)
    try:
        total = (await db.execute(q)).scalar_one()
    except SQLAlchemyError:
        logger.exception("PEF 건수 조회 실패: search=%s", safe_search)
        raise HTTPException(status_code=503, detail="PEF 데이터 조회에 실패했습니다")
    logger.debug("PEF 건수 조회: search=%s, total=%d", safe_search, total)
    return PefCountOut(total=total)


@router.get(
    "/transactions/{txn_id}/fi-recommendations",
    response_model=list[FIRecommendationV2],
    responses={
        403: {"description": "접근 권한 없음"},
        404: {"description": "거래를 찾을 수 없음"},
        422: {"description": "거래금액 미설정 또는 유효하지 않은 파라미터"},
        429: {"description": "요청 횟수 초과"},
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
    target_keywords: str | None = Query(
        None,
        max_length=500,
        description="산업 키워드 (쉼표 구분, Tier 1 판정용)",
    ),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_READ_ACCESS),
) -> list[FIRecommendationV2]:
    """FI 자동 매핑 v2 — GP 프로필 기반 Tier 분류.

    2021년 이후 결성 펀드를 GP별로 그룹핑한 뒤,
    GP의 최소 펀드 약정총액이 target × lower ~ target × upper 범위인
    GP를 추천한다. GP 프로필이 있으면 Tier 1/2를 분류한다.
    (단위: 억원)
    """
    # ── Rate Limiting ──────────────────────────────────────────
    fi_rate_limiter.check(claims.email or claims.user_id or "unknown")

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

    # ── 단위 변환: estimated_deal_value(원) → 억원 ────────────────
    # PEF total_committed_capital은 억원 단위 (금감원 공시 기준)
    target_amount = target_amount / Decimal("100000000")

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
        if txn.target_company_name and len(txn.target_company_name.strip()) >= 2:
            escaped_name = txn.target_company_name.strip()[:200].replace("%", r"\%").replace("_", r"\_")
            q = q.where(~PefFundRegistry.pef_name.ilike(f"%{escaped_name}%", escape="\\"))

    try:
        pefs = list((await db.execute(q)).scalars().all())
    except SQLAlchemyError:
        logger.exception("FI 추천 DB 조회 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="추천 데이터 조회에 실패했습니다")

    # ── GP 프로필 기반 Tier 분류 매칭 (v2) ─────────────────────
    keywords: list[str] | None = None
    if target_keywords:
        keywords = fi_mapping_service.parse_industry_keywords(target_keywords)
    elif txn.industry:
        parsed = fi_mapping_service.parse_industry_keywords(txn.industry.strip())
        keywords = parsed if parsed else None

    try:
        results = await fi_mapping_service.recommend_fi(
            db=db,
            pefs=pefs,
            target_amount=target_amount,
            lower_multiplier=lower_multiplier,
            upper_multiplier=upper_multiplier,
            target_keywords=keywords,
            limit=limit,
        )
    except SQLAlchemyError:
        logger.exception("FI GP 프로필 매핑 실패: txn_id=%s", txn_id)
        raise HTTPException(status_code=503, detail="FI 매핑 중 데이터베이스 오류가 발생했습니다")

    # ── Audit 기록 ─────────────────────────────────────────────
    try:
        await audit_service.record(
            db,
            entity_type="Transaction",
            entity_id=txn_id,
            action=AuditAction.READ,
            actor_email=claims.email or claims.user_id or "unknown",
            new_value={"action": "fi_recommendations", "matched_gps": len(results)},
        )
        await db.commit()
    except Exception:
        logger.exception("FI 추천 감사 로그 기록 실패 (결과 반환은 정상 진행)")

    logger.info(
        "FI 추천 완료: txn_id=%s, target=%s억, matched_gps=%d, total_funds=%d",
        txn_id,
        target_amount,
        len(results),
        sum(r.fund_count for r in results),
    )
    return results
