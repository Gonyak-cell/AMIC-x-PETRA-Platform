"""API 키 라우트 테스트 (test_routes_api_keys.py).

> 마지막 수정: 2026-02-10 19:30:00

POST/GET/DELETE /api/v1/api-keys 엔드포인트 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.db.models.api_key import APIKey
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
    user.email = "test@example.com"
    user.full_name = "Test User"
    return user


def _make_api_key(
    user_id: uuid.UUID,
    name: str = "Test Key",
) -> MagicMock:
    """테스트 APIKey mock."""
    api_key = MagicMock(spec=APIKey)
    api_key.id = uuid.uuid4()
    api_key.user_id = user_id
    api_key.name = name
    api_key.is_active = True
    api_key.expires_at = None
    api_key.created_at = datetime.now(timezone.utc)
    api_key.last_used_at = None
    return api_key


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
    app = create_app()
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    return app


@pytest.fixture
async def unauth_client(unauth_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys
# ---------------------------------------------------------------------------


class TestCreateAPIKey:
    """POST /api/v1/api-keys 테스트."""

    @pytest.mark.asyncio
    async def test_create_api_key_201(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """API 키 생성 시 201."""
        api_key = _make_api_key(user_id=test_user.id, name="My Key")

        with patch(
            "src.api.routes.api_keys.APIKeyService.create",
            new_callable=AsyncMock,
            return_value=(api_key, "imgen_raw_key_123"),
        ):
            response = await route_client.post(
                "/api/v1/api-keys",
                json={"name": "My Key", "expires_days": None},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Key"
        assert data["key"] == "imgen_raw_key_123"

    @pytest.mark.asyncio
    async def test_create_api_key_no_auth_401(
        self, unauth_client: AsyncClient
    ) -> None:
        """인증 없이 API 키 생성 시 401."""
        response = await unauth_client.post(
            "/api/v1/api-keys",
            json={"name": "My Key"},
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/api-keys
# ---------------------------------------------------------------------------


class TestListAPIKeys:
    """GET /api/v1/api-keys 테스트."""

    @pytest.mark.asyncio
    async def test_list_api_keys_200(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """API 키 목록 조회 시 200."""
        keys = [
            _make_api_key(user_id=test_user.id, name="Key 1"),
            _make_api_key(user_id=test_user.id, name="Key 2"),
        ]

        with patch(
            "src.api.routes.api_keys.APIKeyService.list_keys",
            new_callable=AsyncMock,
            return_value=(keys, 2),
        ):
            response = await route_client.get("/api/v1/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# DELETE /api/v1/api-keys/{key_id}
# ---------------------------------------------------------------------------


class TestRevokeAPIKey:
    """DELETE /api/v1/api-keys/{key_id} 테스트."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_204(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """API 키 비활성화 시 204."""
        key_id = uuid.uuid4()

        with patch(
            "src.api.routes.api_keys.APIKeyService.revoke",
            new_callable=AsyncMock,
        ):
            response = await route_client.delete(
                f"/api/v1/api-keys/{key_id}"
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found_404(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """존재하지 않는 키 비활성화 시 404."""
        key_id = uuid.uuid4()

        with patch(
            "src.api.routes.api_keys.APIKeyService.revoke",
            new_callable=AsyncMock,
            side_effect=NotFoundError("APIKey", str(key_id)),
        ):
            response = await route_client.delete(
                f"/api/v1/api-keys/{key_id}"
            )

        assert response.status_code == 404
