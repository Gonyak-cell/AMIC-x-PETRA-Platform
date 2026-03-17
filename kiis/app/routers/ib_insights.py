"""IB 인사이트 API 라우터

GP 세부정보 페이지에서 호출할 IB 매체 인사이트 엔드포인트.
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_active_user, get_jwt_claims
from app.models.ib_article import (
    IB_CRAWL_LOCK_KEY,
    IB_CRAWL_LOCK_TTL,
    IBArticle,
)
from app.schemas.ib_insight import (
    IBArticleItem,
    IBArticleListResponse,
    IBCollectResponse,
    IBInsightResponse,
)
from app.services.ib_crawl_service import IBCrawlService
from app.services.ib_insight_service import IBInsightService

# source 파라미터 유효 값 타입
IBSourceFilter = Literal["investchosun", "dealsite", "ibtomato", "bizwatch", "kmnanews"]

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_jwt_claims)])

# 서비스 싱글턴 (lifespan에서 관리하지 않으므로 lazy init)
_crawl_service: IBCrawlService | None = None
_insight_service: IBInsightService | None = None

CACHE_TTL_INSIGHTS = 3600  # 1시간


def _get_crawl_service() -> IBCrawlService:
    global _crawl_service
    if _crawl_service is None:
        _crawl_service = IBCrawlService()
    return _crawl_service


def _get_insight_service() -> IBInsightService:
    global _insight_service
    if _insight_service is None:
        _insight_service = IBInsightService()
    return _insight_service


async def close_ib_services() -> None:
    """앱 종료 시 IB 서비스 리소스를 정리한다."""
    global _crawl_service
    if _crawl_service is not None:
        await _crawl_service.close()
        _crawl_service = None


@router.get(
    "/gps/{corp_code}/ib-insights",
    response_model=IBInsightResponse,
    summary="GP별 IB 인사이트 조회",
    description="IB 전문 매체 기사를 Fact/Opinion으로 분리하여 반환합니다.",
)
async def get_gp_ib_insights(
    corp_code: str,
    months: int = Query(6, ge=1, le=24, description="조회 기간 (개월)"),
    category: str | None = Query(None, description="카테고리 필터"),
    db: AsyncSession = Depends(get_db),
) -> IBInsightResponse:
    # Redis 캐싱
    redis = get_redis()
    cache_key = f"ib:insights:{corp_code}:{months}:{category or 'all'}"
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return IBInsightResponse(**json.loads(cached))
        except Exception:
            logger.debug("IB 인사이트 캐시 조회 실패", exc_info=True)

    service = _get_insight_service()
    result = await service.get_insights_for_gp(db, corp_code, months, category)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Company not found: {corp_code}")

    response = IBInsightResponse(**result)

    # 캐시 저장
    if redis:
        try:
            await redis.set(cache_key, response.model_dump_json(), ex=CACHE_TTL_INSIGHTS)
        except Exception:
            logger.debug("IB 인사이트 캐시 저장 실패", exc_info=True)

    return response


@router.get(
    "/ib-articles",
    response_model=IBArticleListResponse,
    summary="IB 기사 목록 조회",
)
async def list_ib_articles(
    source: IBSourceFilter | None = Query(None, description="매체 필터"),
    category: str | None = Query(None, description="섹션 필터 (ma, governance, fund)"),
    insight_category: str | None = Query(None, description="레거시 IB 인사이트 카테고리 필터"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> IBArticleListResponse:
    filters = []
    if source:
        filters.append(IBArticle.source == source)
    if category:
        # 3섹션 필터 → section_primary
        filters.append(IBArticle.section_primary == category)
    if insight_category:
        # 레거시 5분류 필터 → category (기존 IB 인사이트)
        filters.append(IBArticle.category == insight_category)

    # 미분류(section_primary=NULL) 기사는 뉴스피드에서 제외
    if not insight_category:
        filters.append(IBArticle.section_primary.is_not(None))

    where_clause = and_(*filters) if filters else True

    # Total count
    count_stmt = select(func.count()).select_from(IBArticle).where(where_clause)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Items
    stmt = (
        select(IBArticle)
        .where(where_clause)
        .order_by(IBArticle.published_at.desc().nullslast())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    section_display = {"ma": "M&A", "governance": "거버넌스", "fund": "펀드"}

    items = [
        IBArticleItem(
            id=a.id,
            title=a.title,
            lead_text=a.lead_text,
            canonical_url=a.canonical_url,
            source=a.source,
            published_at=a.published_at,
            category=a.section_primary,
            category_display=section_display.get(a.section_primary, "미분류") if a.section_primary else "미분류",
            labels=json.loads(a.section_labels_json) if a.section_labels_json else [],
            scores={
                k: v.get("final_score", 0) for k, v in json.loads(a.section_scores_json).get("sections", {}).items()
            }
            if a.section_scores_json
            else {},
            insight_category=a.category,
            insight_domain=a.domain,
            sentiment_score=a.sentiment_score,
            is_paywalled=a.is_paywalled,
        )
        for a in articles
    ]

    return IBArticleListResponse(items=items, total=total, page=page, size=size)


@router.post(
    "/ib-articles/collect",
    response_model=IBCollectResponse,
    summary="IB 기사 수동 수집 트리거",
)
async def collect_ib_articles(
    source: IBSourceFilter | None = Query(None, description="특정 매체만 수집"),
    db: AsyncSession = Depends(get_db),
    _user: object = Depends(get_current_active_user),
) -> IBCollectResponse:
    # 동시 수집 방지 Redis Lock
    redis = get_redis()
    if redis:
        try:
            acquired = await redis.set(IB_CRAWL_LOCK_KEY, "1", nx=True, ex=IB_CRAWL_LOCK_TTL)
            if not acquired:
                raise HTTPException(status_code=409, detail="IB 수집이 이미 진행 중입니다.")
        except HTTPException:
            raise
        except Exception:
            logger.debug("IB 수집 Lock 획득 실패 (Redis 미가용), Lock 없이 진행", exc_info=True)

    try:
        crawl_svc = _get_crawl_service()
        insight_svc = _get_insight_service()

        # 수집
        results = await crawl_svc.collect_all(db, source_filter=source)

        # 미분류 기사 NLP 처리 (classify_unprocessed 내부에서 commit)
        classified = await insight_svc.classify_unprocessed(db)

        # 관련 캐시 무효화
        if redis:
            try:
                async for key in redis.scan_iter(match="ib:insights:*"):
                    await redis.delete(key)
            except Exception:
                logger.debug("IB 캐시 무효화 실패", exc_info=True)

        return IBCollectResponse(results=results, classified=classified)
    finally:
        # Lock 해제
        if redis:
            try:
                await redis.delete(IB_CRAWL_LOCK_KEY)
            except Exception:
                logger.debug("IB 수집 Lock 해제 실패", exc_info=True)
