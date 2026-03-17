"""뉴스 피드 통합 서비스 — KIIS IB 기사 프록시 + CF 소스 병합 + Redis 캐싱.

Phase A: KIIS GET /api/v1/ib-articles 프록시
Phase B: Cloudflare /crawl 추가 소스 (deal-mgmt DB 조회)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.redis import get_redis
from app.schemas.news_feed import (
    NewsFeedItem,
    NewsFeedResponse,
    get_category_display,
    get_source_display,
    get_source_type,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 600  # 10분
_KIIS_TIMEOUT = 10.0  # seconds


def _format_kiis_http_error(status_code: int) -> str:
    """Map KIIS upstream HTTP errors to user-facing messages."""
    if status_code in {401, 402, 403}:
        return "KIIS 뉴스 소스 인증 또는 이용 권한을 확인할 수 없습니다."
    if status_code >= 500:
        return "KIIS 뉴스 소스를 일시적으로 불러오지 못했습니다."
    return "KIIS 뉴스 소스를 불러오지 못했습니다."


async def fetch_news_feed(
    *,
    source: str | None = None,
    source_type: str | None = None,
    category: str | None = None,
    page: int = 1,
    size: int = 10,
    jwt_token: str | None = None,
) -> NewsFeedResponse:
    """KIIS IB 기사를 프록시 조회하고 Redis 캐싱을 적용한다.

    Args:
        source: 매체 필터 (investchosun, dealsite, ...)
        source_type: 소스 유형 필터 (kiis, cloudflare, all)
        category: 카테고리 필터 (deal_progress, ...)
        page: 페이지 번호
        size: 페이지 크기
        jwt_token: 프론트엔드 JWT (KIIS API 인증용)

    Returns:
        NewsFeedResponse
    """
    cache_key = f"news:feed:{source or 'all'}:{category or 'all'}:{page}:{size}"

    # ── 1. Redis 캐시 확인 ──
    redis = get_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return NewsFeedResponse(
                    items=[NewsFeedItem(**item) for item in data["items"]],
                    total=data["total"],
                    cached=True,
                    error=None,
                )
        except Exception:
            logger.debug("뉴스 피드 캐시 조회 실패", exc_info=True)

    # ── 2. KIIS API 호출 ──
    items, total, error = await _fetch_from_kiis(
        source=source,
        category=category,
        page=page,
        size=size,
        jwt_token=jwt_token,
    )

    if error and redis:
        # KIIS 장애 시 stale cache 반환 시도
        try:
            stale = await redis.get(f"news:stale:{source or 'all'}:{category or 'all'}")
            if stale:
                data = json.loads(stale)
                return NewsFeedResponse(
                    items=[NewsFeedItem(**item) for item in data["items"]],
                    total=data["total"],
                    cached=True,
                    error=f"KIIS 연결 장애 — 캐시된 데이터 표시 중: {error}",
                )
        except Exception:
            logger.debug("stale 캐시 조회 실패", exc_info=True)

    response = NewsFeedResponse(items=items, total=total, cached=False, error=error)

    # ── 3. Redis 캐시 저장 ──
    if redis and items:
        try:
            payload = json.dumps(
                {"items": [item.model_dump(mode="json") for item in items], "total": total},
                ensure_ascii=False,
            )
            await redis.set(cache_key, payload, ex=_CACHE_TTL)
            # stale 캐시도 갱신 (TTL 1시간 — 장애 대비)
            await redis.set(
                f"news:stale:{source or 'all'}:{category or 'all'}",
                payload,
                ex=3600,
            )
        except Exception:
            logger.debug("뉴스 피드 캐시 저장 실패", exc_info=True)

    return response


async def _fetch_from_kiis(
    *,
    source: str | None,
    category: str | None,
    page: int,
    size: int,
    jwt_token: str | None,
) -> tuple[list[NewsFeedItem], int, str | None]:
    """KIIS GET /api/v1/ib-articles 호출 → NewsFeedItem 리스트 변환."""
    kiis_base = settings.KIIS_API_URL.rstrip("/")
    url = f"{kiis_base}/ib-articles"

    params: dict[str, Any] = {"page": page, "size": size}
    if source:
        params["source"] = source
    if category:
        params["category"] = category

    headers: dict[str, str] = {}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    try:
        async with httpx.AsyncClient(timeout=_KIIS_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("KIIS IB 기사 API HTTP 에러: %s %s", exc.response.status_code, exc.response.text[:200])
        return [], 0, _format_kiis_http_error(exc.response.status_code)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
        logger.warning("KIIS IB 기사 API 연결 실패: %s", exc)
        return [], 0, f"KIIS 연결 실패: {type(exc).__name__}"
    except Exception as exc:
        logger.exception("KIIS IB 기사 API 예상치 못한 에러")
        return [], 0, f"KIIS 에러: {exc}"

    # KIIS 응답 → NewsFeedItem 변환
    raw_items = data.get("items", [])
    total = data.get("total", len(raw_items))

    items: list[NewsFeedItem] = []
    for raw in raw_items:
        src = raw.get("source", "unknown")
        cat = raw.get("category")
        items.append(
            NewsFeedItem(
                id=f"kiis-{raw.get('id', 0)}",
                title=raw.get("title", ""),
                lead_text=raw.get("lead_text"),
                canonical_url=raw.get("canonical_url", ""),
                source=src,
                source_display=get_source_display(src),
                source_type=get_source_type(src),
                published_at=raw.get("published_at"),
                category=cat,
                category_display=get_category_display(cat),
                is_paywalled=raw.get("is_paywalled", False),
                markdown_available=False,
            )
        )

    return items, total, None


# ── Phase B: Cloudflare 소스 DB 조회 ──────────────────


async def _fetch_from_cf_db(
    *,
    source: str | None,
    category: str | None,
    page: int,
    size: int,
) -> tuple[list[NewsFeedItem], int]:
    """deal-mgmt DB에서 Cloudflare 수집 기사를 조회한다."""
    from sqlalchemy import func, select

    from app.core.database import async_session_factory
    from app.models.cf_news_article import CFNewsArticle
    from app.schemas.news_feed import CF_SOURCES

    filters = []
    if source:
        filters.append(CFNewsArticle.source == source)
    elif CF_SOURCES:
        filters.append(CFNewsArticle.source.in_(CF_SOURCES))
    if category:
        filters.append(CFNewsArticle.category == category)

    async with async_session_factory() as db:
        # Total count
        count_q = select(func.count()).select_from(CFNewsArticle)
        for f in filters:
            count_q = count_q.where(f)
        total = (await db.execute(count_q)).scalar() or 0

        # Items
        q = select(CFNewsArticle).order_by(CFNewsArticle.published_at.desc().nullslast())
        for f in filters:
            q = q.where(f)
        q = q.offset((page - 1) * size).limit(size)
        rows = (await db.execute(q)).scalars().all()

    items: list[NewsFeedItem] = []
    for row in rows:
        items.append(
            NewsFeedItem(
                id=f"cf-{row.id}",
                title=row.title,
                lead_text=row.lead_text,
                canonical_url=row.canonical_url,
                source=row.source,
                source_display=get_source_display(row.source),
                source_type="cloudflare",
                published_at=row.published_at,
                category=row.category,
                category_display=get_category_display(row.category),
                is_paywalled=row.is_paywalled,
                markdown_available=bool(row.markdown_content),
            )
        )
    return items, total


async def fetch_merged_news_feed(
    *,
    source: str | None = None,
    source_type: str | None = None,
    category: str | None = None,
    page: int = 1,
    size: int = 10,
    jwt_token: str | None = None,
) -> NewsFeedResponse:
    """KIIS + Cloudflare 소스를 병합하여 반환한다.

    source_type="kiis"이면 KIIS만, "cloudflare"이면 CF만, None/"all"이면 양쪽 병합.
    """
    from app.schemas.news_feed import KIIS_SOURCES as _KIIS_SOURCES

    # source_type에 따라 분기
    want_kiis = source_type in (None, "all", "kiis")
    want_cf = source_type in (None, "all", "cloudflare") and settings.CF_CRAWL_ENABLED

    # 특정 소스가 지정된 경우 해당 타입만
    if source:
        if source in _KIIS_SOURCES:
            want_kiis, want_cf = True, False
        else:
            want_kiis, want_cf = False, True

    # ── 단일 소스 모드 → 해당 소스의 pagination을 그대로 위임 ──
    if want_kiis and not want_cf:
        items, total, err = await _fetch_from_kiis(
            source=source if source and source in _KIIS_SOURCES else None,
            category=category,
            page=page,
            size=size,
            jwt_token=jwt_token,
        )
        return NewsFeedResponse(items=items, total=total, cached=False, error=err)

    if want_cf and not want_kiis:
        items, total = await _fetch_from_cf_db(
            source=source if source and source not in _KIIS_SOURCES else None,
            category=category,
            page=page,
            size=size,
        )
        return NewsFeedResponse(items=items, total=total, cached=False, error=None)

    if not want_kiis and not want_cf:
        return NewsFeedResponse(items=[], total=0, cached=False, error=None)

    # ── 병합 모드 → 충분한 후보를 가져와 merge-sort 후 page slice ──
    fetch_size = page * size

    kiis_items, kiis_total, kiis_error = await _fetch_from_kiis(
        source=None,
        category=category,
        page=1,
        size=fetch_size,
        jwt_token=jwt_token,
    )

    cf_items, cf_total = await _fetch_from_cf_db(
        source=None,
        category=category,
        page=1,
        size=fetch_size,
    )

    # 병합 + published_at 기준 정렬
    merged = kiis_items + cf_items
    merged.sort(key=lambda x: x.published_at or "", reverse=True)

    # 현재 페이지 슬라이스
    start = (page - 1) * size
    page_items = merged[start : start + size]

    merged_error = kiis_error
    if kiis_error and page_items:
        merged_error = "일부 뉴스 소스를 불러오지 못해 사용 가능한 기사만 표시 중입니다."

    return NewsFeedResponse(
        items=page_items,
        total=kiis_total + cf_total,
        cached=False,
        error=merged_error,
    )
