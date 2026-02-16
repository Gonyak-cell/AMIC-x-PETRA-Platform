"""통합 검색 API 라우터

ElasticSearch 기반 통합 검색, 리인덱싱, 인덱스 상태 조회 엔드포인트를 제공한다.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.schemas.search import (
    IndexStatusResponse,
    ReindexResponse,
    SearchResponse,
    SearchResultItem,
)
from app.services.search_service import SearchService

router = APIRouter()


def get_search_service() -> SearchService:
    """검색 서비스 팩토리"""
    return SearchService()


@router.get(
    "",
    response_model=SearchResponse,
    summary="통합 검색",
    description="ElasticSearch 기반으로 기업, 펀드, 뉴스, 딜 데이터를 통합 검색한다.",
)
async def search(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    type: str | None = Query(None, description="검색 대상 (companies/funds/news/deals)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 결과 수"),
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """통합 검색을 수행한다. type을 지정하지 않으면 모든 인덱스를 검색한다."""
    items, total = await service.search(q=q, type=type, page=page, size=size)

    return SearchResponse(
        total=total,
        page=page,
        size=size,
        query=q,
        items=[SearchResultItem(**item) for item in items],
    )


@router.post(
    "/reindex",
    response_model=ReindexResponse,
    summary="전체 리인덱싱",
    description="DB의 모든 데이터를 ElasticSearch에 리인덱싱한다. admin 권한 필요.",
)
async def reindex(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role("admin")),
    service: SearchService = Depends(get_search_service),
) -> ReindexResponse:
    """DB에서 모든 데이터를 읽어 ES에 리인덱싱한다."""
    counts = await service.reindex_all(db)

    return ReindexResponse(
        companies=counts.get("companies", 0),
        funds=counts.get("funds", 0),
        news=counts.get("news", 0),
        deals=counts.get("deals", 0),
    )


@router.get(
    "/status",
    response_model=IndexStatusResponse,
    summary="인덱스 상태 조회",
    description="ElasticSearch 각 인덱스의 문서 수와 크기를 조회한다. admin 권한 필요.",
)
async def index_status(
    _current_user: User = Depends(require_role("admin")),
    service: SearchService = Depends(get_search_service),
) -> IndexStatusResponse:
    """각 ES 인덱스의 상태 정보를 반환한다."""
    indices = await service.get_index_status()

    return IndexStatusResponse(indices=indices)
