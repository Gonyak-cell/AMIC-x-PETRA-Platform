from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.news import NewsArticle
from app.schemas.news import NewsCollectResponse, NewsItem, NewsListItem, NewsListResponse
from app.services.news_service import NewsService

router = APIRouter()


def get_news_service() -> NewsService:
    return NewsService()


@router.get("", response_model=NewsListResponse, summary="뉴스 목록 조회")
async def list_news(
    source: str | None = Query(None, max_length=50, description="출처 필터 (platum, dealsite)"),
    date_from: str | None = Query(None, max_length=10, description="시작일 (YYYY-MM-DD)"),
    date_to: str | None = Query(None, max_length=10, description="종료일 (YYYY-MM-DD)"),
    company_id: int | None = Query(None, description="기업 ID 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
):
    """뉴스 기사 목록을 조회한다.

    출처, 날짜 범위, 관련 기업으로 필터링할 수 있다.
    """
    query = select(NewsArticle)

    if source:
        query = query.where(NewsArticle.source == source)
    if date_from:
        query = query.where(NewsArticle.published_at >= date_from)
    if date_to:
        query = query.where(NewsArticle.published_at <= date_to)
    if company_id:
        query = query.where(NewsArticle.company_id == company_id)

    # 전체 건수
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션 (최신 순)
    query = query.order_by(NewsArticle.published_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    articles = result.scalars().all()

    items = [NewsListItem.model_validate(a) for a in articles]
    return NewsListResponse(total=total, page=page, size=size, items=items)


@router.get("/{article_id}", response_model=NewsItem, summary="뉴스 상세 조회")
async def get_news(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    """특정 뉴스 기사의 상세 정보를 조회한다."""
    result = await db.execute(select(NewsArticle).where(NewsArticle.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail=f"뉴스를 찾을 수 없습니다: {article_id}")

    return NewsItem.model_validate(article)


@router.post("/collect", response_model=list[NewsCollectResponse], summary="뉴스 RSS 수집")
async def collect_news(
    source: str | None = Query(None, max_length=50, description="특정 소스만 수집 (미지정 시 전체)"),
    db: AsyncSession = Depends(get_db),
    service: NewsService = Depends(get_news_service),
):
    """RSS 피드에서 뉴스를 수집한다.

    source를 지정하면 해당 소스만, 미지정 시 전체 소스에서 수집한다.
    """
    results = await service.collect_all(db=db, source_filter=source)
    await service.close()
    return results
