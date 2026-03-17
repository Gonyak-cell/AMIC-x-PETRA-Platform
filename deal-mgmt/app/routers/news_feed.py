"""뉴스 피드 API 라우터 — 대시보드 M&A 뉴스 섹션.

KIIS 기존 4개 IB 소스 + Cloudflare 추가 소스를 통합 제공한다.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import settings
from app.core.security import get_jwt_claims
from app.schemas.news_feed import NewsFeedResponse
from app.services.news_feed_service import fetch_merged_news_feed, fetch_news_feed

router = APIRouter(
    prefix="/news-feed",
    tags=["News Feed"],
    dependencies=[Depends(get_jwt_claims)],
)

# 전체 소스 유효값 (KIIS + CF)
AllSourceFilter = Literal[
    "investchosun",
    "dealsite",
    "ibtomato",
    "bizwatch",
    "hankyung_ib",
    "mk_ib",
    "chosunbiz_ma",
    "thebell",
]

# 소스 유형 필터
SourceTypeFilter = Literal["kiis", "cloudflare", "all"]

# 카테고리 유효값
CategoryFilter = Literal[
    "ma",
    "governance",
    "fund",
]


@router.get(
    "/latest",
    response_model=NewsFeedResponse,
    summary="M&A 뉴스 피드 최신 목록",
    description=(
        "KIIS IB 매체(인베스트조선, 딜사이트, IB토마토, 블로터) + "
        "Cloudflare 추가 소스(한경IB, 더벨, 매경IB, 조선비즈)의 최신 기사를 조회합니다."
    ),
)
async def get_latest_news(
    request: Request,
    source: AllSourceFilter | None = Query(None, description="매체 필터"),
    source_type: SourceTypeFilter | None = Query(None, description="소스 유형 필터 (kiis/cloudflare/all)"),
    category: CategoryFilter | None = Query(None, description="카테고리 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=50, description="페이지 크기"),
) -> NewsFeedResponse:
    # Authorization 헤더에서 JWT 토큰 추출 → KIIS API 포워딩
    auth_header = request.headers.get("authorization", "")
    jwt_token: str | None = None
    if auth_header.lower().startswith("bearer "):
        jwt_token = auth_header[7:]
    else:
        # 쿠키 기반 인증 폴백 — 프론트엔드가 Authorization 헤더 없이
        # httpOnly 쿠키로만 인증하므로, 쿠키에서 JWT를 추출하여 KIIS로 포워딩
        jwt_token = request.cookies.get("access_token")

    # CF 활성화 시 병합 API, 비활성화 시 KIIS 전용
    if settings.CF_CRAWL_ENABLED:
        return await fetch_merged_news_feed(
            source=source,
            source_type=source_type,
            category=category,
            page=page,
            size=size,
            jwt_token=jwt_token,
        )

    return await fetch_news_feed(
        source=source,
        source_type=source_type,
        category=category,
        page=page,
        size=size,
        jwt_token=jwt_token,
    )
