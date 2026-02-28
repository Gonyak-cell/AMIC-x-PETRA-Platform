"""IB 인사이트 라우터 테스트

API 엔드포인트 응답 구조 + 스키마 검증.
- 단위 테스트: SQLite async_session + dependency_overrides (CI 실행)
- 통합 테스트: 실제 PostgreSQL client fixture (integration 마크)
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.main import app
from app.models.company import Company
from app.models.ib_article import IBArticle
from app.services.ib_crawl_service import generate_url_hash

# --- 단위 테스트용 fixture (non-integration) ---


@pytest.fixture
async def unit_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    """SQLite 세션을 주입하는 단위 테스트 클라이언트.

    get_db → async_session 오버라이드로 PostgreSQL 불필요.
    get_current_active_user → Mock 유저로 인증 우회.
    IBInsightService → Mock (Kiwi 모델 로딩 회피).
    """
    import app.routers.ib_insights as ib_router_module

    async def _override_get_db() -> AsyncGenerator:
        yield async_session

    mock_user = MagicMock()
    mock_user.is_active = True

    # IBInsightService Mock (kiwipiepy Kiwi 모델 초기화 회피)
    mock_insight_svc = MagicMock()
    mock_insight_svc.get_insights_for_gp = AsyncMock(return_value=None)
    mock_insight_svc.classify_unprocessed = AsyncMock(return_value=0)
    original_get_insight = ib_router_module._get_insight_service

    def _mock_get_insight_service() -> MagicMock:
        return mock_insight_svc

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    ib_router_module._get_insight_service = _mock_get_insight_service  # type: ignore[assignment]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    ib_router_module._get_insight_service = original_get_insight  # type: ignore[assignment]


# --- 단위 테스트 (CI 실행) ---


@pytest.mark.asyncio
async def test_unit_ib_articles_empty(unit_client: AsyncClient) -> None:
    """IB 기사 목록 — 빈 응답 (단위)"""
    resp = await unit_client.get("/api/v1/ib-articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_unit_ib_insights_not_found(unit_client: AsyncClient) -> None:
    """존재하지 않는 GP — 404 (단위)"""
    resp = await unit_client.get("/api/v1/gps/99999999/ib-insights")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unit_ib_articles_list_with_data(unit_client: AsyncClient, async_session) -> None:
    """IB 기사 목록 — 데이터 존재 시 (단위)"""
    article = IBArticle(
        title="단위 테스트 기사",
        lead_text="단위 리드 텍스트.",
        source="dealsite",
        canonical_url="https://example.com/unit/1",
        url_hash=generate_url_hash("https://example.com/unit/1"),
        is_paywalled=False,
        category="deal_progress",
        domain="fact",
        published_at=datetime.now(UTC),
    )
    async_session.add(article)
    await async_session.commit()

    resp = await unit_client.get("/api/v1/ib-articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["title"] == "단위 테스트 기사"
    assert item["category_display"] == "딜 진행"
    assert item["canonical_url"] == "https://example.com/unit/1"


@pytest.mark.asyncio
async def test_unit_collect_endpoint(unit_client: AsyncClient) -> None:
    """POST /ib-articles/collect 수집 엔드포인트 (단위)"""
    mock_crawl = MagicMock()
    mock_crawl.collect_all = AsyncMock(return_value={"dealsite": {"collected": 5, "new": 3, "duplicates": 2}})
    mock_insight = MagicMock()
    mock_insight.classify_unprocessed = AsyncMock(return_value=2)

    with (
        patch("app.routers.ib_insights._get_crawl_service", return_value=mock_crawl),
        patch("app.routers.ib_insights._get_insight_service", return_value=mock_insight),
        patch("app.routers.ib_insights.get_redis", return_value=None),
    ):
        resp = await unit_client.post("/api/v1/ib-articles/collect")

    assert resp.status_code == 200
    data = resp.json()
    assert data["classified"] == 2
    assert data["results"]["dealsite"]["new"] == 3
    assert data["results"]["dealsite"]["collected"] == 5


@pytest.mark.asyncio
async def test_unit_collect_requires_auth(async_session) -> None:
    """POST /ib-articles/collect — 미인증 시 401 반환"""

    async def _override_get_db() -> AsyncGenerator:
        yield async_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.post("/api/v1/ib-articles/collect")

    app.dependency_overrides.clear()
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ib_articles_empty(client) -> None:
    """IB 기사 목록 — 빈 응답"""
    resp = await client.get("/api/v1/ib-articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ib_insights_not_found(client) -> None:
    """존재하지 않는 GP의 인사이트 조회 — 404"""
    resp = await client.get("/api/v1/gps/99999999/ib-insights")
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ib_articles_list_with_data(client, async_session) -> None:
    """IB 기사 목록 — 데이터 존재 시"""
    article = IBArticle(
        title="라우터 테스트 기사",
        lead_text="리드 텍스트입니다.",
        source="dealsite",
        canonical_url="https://example.com/router-test/1",
        url_hash=generate_url_hash("https://example.com/router-test/1"),
        is_paywalled=False,
        category="deal_progress",
        domain="fact",
        published_at=datetime.now(UTC),
    )
    async_session.add(article)
    await async_session.commit()

    resp = await client.get("/api/v1/ib-articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["title"] == "라우터 테스트 기사"
    assert item["source"] == "dealsite"
    assert item["canonical_url"] == "https://example.com/router-test/1"
    assert "category_display" in item


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ib_articles_source_filter(client, async_session) -> None:
    """IB 기사 목록 — 소스 필터링"""
    for i, source in enumerate(["dealsite", "bloter", "dealsite"]):
        article = IBArticle(
            title=f"필터 테스트 {i}",
            source=source,
            canonical_url=f"https://example.com/filter/{i}",
            url_hash=generate_url_hash(f"https://example.com/filter/{i}"),
            is_paywalled=False,
        )
        async_session.add(article)
    await async_session.commit()

    resp = await client.get("/api/v1/ib-articles", params={"source": "dealsite"})
    data = resp.json()
    assert data["total"] >= 2
    for item in data["items"]:
        assert item["source"] == "dealsite"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ib_insights_response_schema(client, async_session) -> None:
    """GP 인사이트 응답 스키마 검증"""
    company = Company(corp_code="00888001", corp_name="라우터테스트운용")
    async_session.add(company)
    await async_session.flush()

    fact_article = IBArticle(
        title="인수 추진 기사",
        source="dealsite",
        canonical_url="https://example.com/schema/fact",
        url_hash=generate_url_hash("https://example.com/schema/fact"),
        is_paywalled=False,
        category="deal_progress",
        domain="fact",
        company_id=company.id,
        published_at=datetime.now(UTC),
    )
    opinion_article = IBArticle(
        title="평판 논란 기사",
        source="investchosun",
        canonical_url="https://example.com/schema/opinion",
        url_hash=generate_url_hash("https://example.com/schema/opinion"),
        is_paywalled=False,
        category="reputation",
        domain="opinion",
        company_id=company.id,
        published_at=datetime.now(UTC),
    )
    async_session.add_all([fact_article, opinion_article])
    await async_session.commit()

    resp = await client.get("/api/v1/gps/00888001/ib-insights")
    assert resp.status_code == 200
    data = resp.json()

    # 스키마 필드 확인
    assert data["corp_code"] == "00888001"
    assert data["corp_name"] == "라우터테스트운용"
    assert data["total_articles"] == 2
    assert isinstance(data["facts"], list)
    assert isinstance(data["opinions"], list)
    assert len(data["facts"]) == 1
    assert len(data["opinions"]) == 1
    assert "disclaimer" in data
    assert "당사의 공식 입장" in data["disclaimer"]

    # Fact 아이템 필드
    fact = data["facts"][0]
    assert fact["category"] == "deal_progress"
    assert "canonical_url" in fact
    assert "sentiment_score" in fact
