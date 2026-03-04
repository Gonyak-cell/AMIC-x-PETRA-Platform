"""Companies 라우트 테스트 (T-I17).

> 마지막 수정: 2026-02-10 23:45:00

POST/GET /api/v1/companies 엔드포인트 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.db.models.company import Company
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.exceptions import NotFoundError


def _make_user(role: str = "USER") -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_company(**kwargs) -> MagicMock:
    """테스트 Company mock."""
    now = datetime.now(timezone.utc)
    company = MagicMock(spec=Company)
    company.id = kwargs.get("id", uuid.uuid4())
    company.corp_code = kwargs.get("corp_code", "00123456")
    company.corp_name = kwargs.get("corp_name", "테스트 주식회사")
    company.corp_name_en = kwargs.get("corp_name_en", "Test Corp")
    company.stock_code = kwargs.get("stock_code", "123456")
    company.industry = kwargs.get("industry", "tech")
    company.homepage_url = kwargs.get("homepage_url", "https://test.co.kr")
    company.fetch_status = kwargs.get("fetch_status", "PENDING")
    company.last_fetched_at = kwargs.get("last_fetched_at")
    company.cache_expires_at = kwargs.get("cache_expires_at")
    company.created_at = now
    company.updated_at = now
    return company


@pytest.fixture
def test_user() -> MagicMock:
    return _make_user()


@pytest.fixture
def route_app(test_user):
    """라우트 테스트용 앱 (인증 우회)."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    return app


@pytest.fixture
async def route_client(route_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=route_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def unauth_app():
    """인증 우회 없는 앱."""
    return create_app()


@pytest.fixture
async def unauth_client(unauth_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# POST /api/v1/companies
# ---------------------------------------------------------------------------


class TestFetchCompany:
    """POST /api/v1/companies 테스트."""

    @pytest.mark.asyncio
    async def test_fetch_company_returns_202(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """정상 수집 시작 시 202."""
        company = _make_company()
        with patch(
            "src.api.routes.companies.CompanyService.fetch_company",
            new_callable=AsyncMock,
            return_value=company,
        ):
            response = await route_client.post(
                "/api/v1/companies",
                json={"corp_code": "00123456"},
            )
        assert response.status_code == 202
        data = response.json()
        assert data["corp_code"] == "00123456"

    @pytest.mark.asyncio
    async def test_fetch_company_invalid_corp_code(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """잘못된 corp_code 시 422."""
        response = await route_client.post(
            "/api/v1/companies",
            json={"corp_code": "ABCDEFGH"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_fetch_company_unauthorized(self, unauth_client: AsyncClient) -> None:
        """인증 없이 요청 시 401."""
        response = await unauth_client.post(
            "/api/v1/companies",
            json={"corp_code": "00123456"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/companies/{corp_code}
# ---------------------------------------------------------------------------


class TestGetCompany:
    """GET /api/v1/companies/{corp_code} 테스트."""

    @pytest.mark.asyncio
    async def test_get_company_cache_hit(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """캐시된 데이터 조회 성공."""
        company = _make_company(fetch_status="COMPLETED")
        with patch(
            "src.api.routes.companies.CompanyService.get_company",
            new_callable=AsyncMock,
            return_value=company,
        ):
            response = await route_client.get("/api/v1/companies/00123456")
        assert response.status_code == 200
        assert response.json()["fetch_status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_get_company_not_found(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """존재하지 않는 기업 404."""
        with patch(
            "src.api.routes.companies.CompanyService.get_company",
            new_callable=AsyncMock,
            side_effect=NotFoundError("Company", "99999999"),
        ):
            response = await route_client.get("/api/v1/companies/99999999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_company_cache_expired_triggers_refresh(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """캐시 만료 시 자동 재수집 (REFRESHING 상태)."""
        company = _make_company(fetch_status="REFRESHING")
        with patch(
            "src.api.routes.companies.CompanyService.get_company",
            new_callable=AsyncMock,
            return_value=company,
        ):
            response = await route_client.get("/api/v1/companies/00123456")
        assert response.status_code == 200
        assert response.json()["fetch_status"] == "REFRESHING"
