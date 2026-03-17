"""뉴스 피드 API 라우터 회귀 테스트.

테스트 대상:
- /news-feed/latest 200 응답
- CF_CRAWL_ENABLED on/off에 따른 서비스 분기
- source/category/page/size 쿼리 파라미터 전달
- KIIS 실패 시 error 필드 반환
- stale cache fallback 동작
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.schemas.news_feed import NewsFeedItem

# KIIS가 반환하는 원본 형식의 mock 응답
_KIIS_ARTICLES = {
    "items": [
        {
            "id": 1,
            "title": "테스트 기사 1",
            "lead_text": "리드 텍스트 1",
            "canonical_url": "https://example.com/1",
            "source": "dealsite",
            "published_at": "2026-03-16T09:00:00Z",
            "category": "deal_progress",
            "is_paywalled": False,
        },
        {
            "id": 2,
            "title": "테스트 기사 2",
            "lead_text": None,
            "canonical_url": "https://example.com/2",
            "source": "investchosun",
            "published_at": "2026-03-16T08:30:00Z",
            "category": "reputation",
            "is_paywalled": True,
        },
    ],
    "total": 2,
}


def _make_httpx_response(
    data: dict | None = None,
    status_code: int = 200,
) -> httpx.Response:
    """httpx.Response mock을 생성한다."""
    import json

    resp = httpx.Response(
        status_code=status_code,
        content=json.dumps(data or _KIIS_ARTICLES).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://kiis-test/api/v1/ib-articles"),
    )
    return resp


@pytest.fixture()
def mock_redis_none():
    """Redis 비활성화 (get_redis → None)."""
    with patch("app.services.news_feed_service.get_redis", return_value=None):
        yield


@pytest.fixture()
def mock_kiis_success(mock_redis_none):
    """KIIS API 정상 응답 mock."""
    mock_client = AsyncMock()
    mock_client.get.return_value = _make_httpx_response()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_client):
        yield mock_client


@pytest.fixture()
def mock_kiis_failure(mock_redis_none):
    """KIIS API 연결 실패 mock."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_client):
        yield mock_client


# ── 1. 기본 200 응답 ──────


async def test_latest_returns_200(client, mock_kiis_success) -> None:
    """KIIS 정상 응답 시 200 + 기사 목록을 반환한다."""
    resp = await client.get("/api/v1/news-feed/latest")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "테스트 기사 1"
    assert data["items"][0]["source"] == "dealsite"
    assert data["items"][0]["source_display"] == "딜사이트"
    assert data["items"][0]["source_type"] == "kiis"
    assert data["items"][0]["id"] == "kiis-1"
    assert data["cached"] is False
    assert data["error"] is None


# ── 2. KIIS 실패 시 error 필드 반환 ──────


async def test_kiis_failure_returns_error(client, mock_kiis_failure) -> None:
    """KIIS 연결 실패 시 items=[], error=에러 메시지를 반환한다."""
    resp = await client.get("/api/v1/news-feed/latest")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0
    assert data["error"] is not None
    assert "KIIS" in data["error"]


# ── 3. 쿼리 파라미터 전달 확인 ──────


async def test_kiis_402_returns_friendly_error(client, mock_redis_none) -> None:
    """KIIS 402는 raw status code 대신 사용자 친화 메시지로 변환한다."""
    mock_client = AsyncMock()
    mock_client.get.return_value = _make_httpx_response(
        data={"detail": "Payment Required"},
        status_code=402,
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("app.routers.news_feed.settings") as mock_settings,
    ):
        mock_settings.CF_CRAWL_ENABLED = False
        resp = await client.get("/api/v1/news-feed/latest")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["error"] == "KIIS 뉴스 소스 인증 또는 이용 권한을 확인할 수 없습니다."


async def test_query_params_forwarded(client, mock_kiis_success) -> None:
    """source, category, page, size 파라미터가 KIIS API로 전달된다."""
    resp = await client.get(
        "/api/v1/news-feed/latest",
        params={"source": "dealsite", "category": "deal_progress", "page": 2, "size": 5},
    )
    assert resp.status_code == 200

    # httpx.AsyncClient().get 호출 인자 확인
    call_args = mock_kiis_success.get.call_args
    params = call_args.kwargs.get("params", {})
    assert params["source"] == "dealsite"
    assert params["category"] == "deal_progress"
    assert params["page"] == 2
    assert params["size"] == 5


# ── 4. stale cache fallback (서비스 함수 직접 테스트) ──────


async def test_stale_cache_fallback() -> None:
    """KIIS 실패 + stale cache 존재 시 cached=True, error=경고 메시지를 반환한다."""
    import json

    from app.services.news_feed_service import fetch_news_feed

    stale_payload = json.dumps(
        {
            "items": [
                {
                    "id": "kiis-99",
                    "title": "캐시된 기사",
                    "lead_text": None,
                    "canonical_url": "https://example.com/99",
                    "source": "dealsite",
                    "source_display": "딜사이트",
                    "source_type": "kiis",
                    "published_at": "2026-03-16T00:00:00",
                    "category": None,
                    "category_display": "미분류",
                    "is_paywalled": False,
                    "markdown_available": False,
                },
            ],
            "total": 1,
        }
    )

    # Redis mock: 일반 캐시 없음, stale 캐시 있음
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(
        side_effect=lambda key: stale_payload if "stale" in key else None,
    )

    # KIIS 연결 실패 mock
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.services.news_feed_service.get_redis", return_value=mock_redis),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result = await fetch_news_feed(page=1, size=10)

    assert result.cached is True
    assert result.total == 1
    assert result.items[0].title == "캐시된 기사"
    assert result.error is not None
    assert "캐시된 데이터" in result.error


# ── 5. CF_CRAWL_ENABLED=True 시 fetch_merged_news_feed 호출 ──────


async def test_merged_feed_returns_partial_warning_when_cf_has_items() -> None:
    """merged 모드에서 KIIS 실패 + CF 성공이면 부분 성공 경고를 반환한다."""
    from app.schemas.news_feed import NewsFeedItem
    from app.services.news_feed_service import fetch_merged_news_feed

    cf_item = NewsFeedItem(
        id="cf-1",
        title="CF 기사 1",
        lead_text=None,
        canonical_url="https://example.com/cf-1",
        source="thebell",
        source_display="더벨",
        source_type="cloudflare",
        published_at="2026-03-16T10:00:00Z",
        category="deal_progress",
        category_display="딜 진행",
        is_paywalled=False,
        markdown_available=True,
    )

    with (
        patch("app.services.news_feed_service.settings") as mock_settings,
        patch(
            "app.services.news_feed_service._fetch_from_kiis",
            AsyncMock(return_value=([], 0, "KIIS 뉴스 소스 인증 또는 이용 권한을 확인할 수 없습니다.")),
        ),
        patch(
            "app.services.news_feed_service._fetch_from_cf_db",
            AsyncMock(return_value=([cf_item], 1)),
        ),
    ):
        mock_settings.CF_CRAWL_ENABLED = True
        result = await fetch_merged_news_feed(page=1, size=10)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].id == "cf-1"
    assert result.error == "일부 뉴스 소스를 불러오지 못해 사용 가능한 기사만 표시 중입니다."


async def test_cf_enabled_uses_merged_path(client, mock_kiis_success) -> None:
    """CF_CRAWL_ENABLED=True이면 merged 경로를 사용한다."""
    with patch("app.routers.news_feed.settings") as mock_settings:
        mock_settings.CF_CRAWL_ENABLED = True
        # merged 함수를 mock하여 CF 경로 검증
        mock_merged = AsyncMock()
        mock_merged.return_value = MagicMock(
            items=[],
            total=0,
            cached=False,
            error=None,
            model_dump=lambda **kw: {"items": [], "total": 0, "cached": False, "error": None},
        )
        with patch("app.routers.news_feed.fetch_merged_news_feed", mock_merged):
            resp = await client.get("/api/v1/news-feed/latest")

    assert resp.status_code == 200
    mock_merged.assert_called_once()


# ── 6. 유효하지 않은 source → 422 ──────


async def test_invalid_source_returns_422(client) -> None:
    """유효하지 않은 source 값은 422 Validation Error를 반환한다."""
    resp = await client.get(
        "/api/v1/news-feed/latest",
        params={"source": "invalid_source"},
    )
    assert resp.status_code == 422


# ── 7. Merged mode pagination 검증 ──────


def _make_mock_items(
    prefix: str,
    source: str,
    source_type: str,
    times: list[str],
) -> list[NewsFeedItem]:
    """테스트용 NewsFeedItem 리스트를 생성한다."""
    from app.schemas.news_feed import get_source_display

    return [
        NewsFeedItem(
            id=f"{prefix}-{i}",
            title=f"{prefix} 기사 {i}",
            canonical_url=f"https://example.com/{prefix}/{i}",
            source=source,
            source_display=get_source_display(source),
            source_type=source_type,
            published_at=t,
            category=None,
            category_display="미분류",
        )
        for i, t in enumerate(times, 1)
    ]


# KIIS: 10:00, 08:00, 06:00 (3건)
_MERGE_KIIS = _make_mock_items(
    "kiis",
    "dealsite",
    "kiis",
    ["2026-03-16T10:00:00", "2026-03-16T08:00:00", "2026-03-16T06:00:00"],
)
# CF: 09:00, 07:00, 05:00 (3건)
_MERGE_CF = _make_mock_items(
    "cf",
    "thebell",
    "cloudflare",
    ["2026-03-16T09:00:00", "2026-03-16T07:00:00", "2026-03-16T05:00:00"],
)
# 병합 정렬 기대순: kiis-1(10), cf-1(09), kiis-2(08), cf-2(07), kiis-3(06), cf-3(05)


async def test_merged_page1_returns_first_slice() -> None:
    """merged 모드 page=1, size=3 → 최신 3건을 반환한다."""
    from app.services.news_feed_service import fetch_merged_news_feed

    with (
        patch("app.services.news_feed_service._fetch_from_kiis", new_callable=AsyncMock) as m_kiis,
        patch("app.services.news_feed_service._fetch_from_cf_db", new_callable=AsyncMock) as m_cf,
        patch("app.services.news_feed_service.settings") as m_settings,
    ):
        m_settings.CF_CRAWL_ENABLED = True
        m_kiis.return_value = (_MERGE_KIIS, 3, None)
        m_cf.return_value = (_MERGE_CF, 3)

        result = await fetch_merged_news_feed(page=1, size=3)

    assert len(result.items) == 3
    assert result.total == 6
    assert [it.id for it in result.items] == ["kiis-1", "cf-1", "kiis-2"]


async def test_merged_page2_returns_next_slice() -> None:
    """merged 모드 page=2, size=3 → 다음 3건을 반환한다."""
    from app.services.news_feed_service import fetch_merged_news_feed

    with (
        patch("app.services.news_feed_service._fetch_from_kiis", new_callable=AsyncMock) as m_kiis,
        patch("app.services.news_feed_service._fetch_from_cf_db", new_callable=AsyncMock) as m_cf,
        patch("app.services.news_feed_service.settings") as m_settings,
    ):
        m_settings.CF_CRAWL_ENABLED = True
        m_kiis.return_value = (_MERGE_KIIS, 3, None)
        m_cf.return_value = (_MERGE_CF, 3)

        result = await fetch_merged_news_feed(page=2, size=3)

    assert len(result.items) == 3
    assert result.total == 6
    assert [it.id for it in result.items] == ["cf-2", "kiis-3", "cf-3"]


async def test_merged_total_reflects_both_sources() -> None:
    """merged 모드 total은 양쪽 소스 합산이다."""
    from app.services.news_feed_service import fetch_merged_news_feed

    with (
        patch("app.services.news_feed_service._fetch_from_kiis", new_callable=AsyncMock) as m_kiis,
        patch("app.services.news_feed_service._fetch_from_cf_db", new_callable=AsyncMock) as m_cf,
        patch("app.services.news_feed_service.settings") as m_settings,
    ):
        m_settings.CF_CRAWL_ENABLED = True
        m_kiis.return_value = (_MERGE_KIIS, 30, None)  # KIIS 전체 30건
        m_cf.return_value = (_MERGE_CF, 20)  # CF 전체 20건

        result = await fetch_merged_news_feed(page=1, size=5)

    assert result.total == 50  # 30 + 20


async def test_source_type_kiis_delegates_pagination() -> None:
    """source_type=kiis → KIIS pagination 직접 위임, total = KIIS total."""
    from app.services.news_feed_service import fetch_merged_news_feed

    with (
        patch("app.services.news_feed_service._fetch_from_kiis", new_callable=AsyncMock) as m_kiis,
        patch("app.services.news_feed_service._fetch_from_cf_db", new_callable=AsyncMock) as m_cf,
        patch("app.services.news_feed_service.settings") as m_settings,
    ):
        m_settings.CF_CRAWL_ENABLED = True
        m_kiis.return_value = (_MERGE_KIIS[:2], 25, None)
        m_cf.return_value = ([], 0)

        result = await fetch_merged_news_feed(source_type="kiis", page=2, size=2)

    assert result.total == 25
    m_kiis.assert_called_once()
    m_cf.assert_not_called()
    # page/size가 KIIS에 그대로 전달되는지 확인
    call_kw = m_kiis.call_args.kwargs
    assert call_kw["page"] == 2
    assert call_kw["size"] == 2


async def test_source_type_cloudflare_delegates_pagination() -> None:
    """source_type=cloudflare → CF pagination 직접 위임, total = CF total."""
    from app.services.news_feed_service import fetch_merged_news_feed

    with (
        patch("app.services.news_feed_service._fetch_from_kiis", new_callable=AsyncMock) as m_kiis,
        patch("app.services.news_feed_service._fetch_from_cf_db", new_callable=AsyncMock) as m_cf,
        patch("app.services.news_feed_service.settings") as m_settings,
    ):
        m_settings.CF_CRAWL_ENABLED = True
        m_cf.return_value = (_MERGE_CF[:2], 15)

        result = await fetch_merged_news_feed(source_type="cloudflare", page=3, size=2)

    assert result.total == 15
    m_cf.assert_called_once()
    m_kiis.assert_not_called()
    call_kw = m_cf.call_args.kwargs
    assert call_kw["page"] == 3
    assert call_kw["size"] == 2
