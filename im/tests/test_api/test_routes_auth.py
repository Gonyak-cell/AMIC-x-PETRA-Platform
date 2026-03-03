"""인증 라우트 테스트 (test_routes_auth.py).

> 마지막 수정: 2026-02-10 19:30:00

POST /api/v1/auth/login, /refresh, /logout 엔드포인트 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.exceptions import AuthenticationError


def _make_user(role: str = "USER") -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    user.email = "test@example.com"
    user.full_name = "Test User"
    return user


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
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLoginRoute:
    """POST /api/v1/auth/login 테스트."""

    @pytest.mark.asyncio
    async def test_login_success_200(self, unauth_client: AsyncClient) -> None:
        """정상 로그인 시 200과 httpOnly 쿠키 설정."""
        with patch(
            "src.api.routes.auth.AuthService.login",
            new_callable=AsyncMock,
            return_value={
                "access_token": "access_123",
                "refresh_token": "refresh_123",
            },
        ):
            response = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "password123"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "로그인 성공"
        # 토큰은 httpOnly 쿠키로 전달
        cookies = {c.name: c.value for c in response.cookies.jar}
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_401(
        self, unauth_client: AsyncClient
    ) -> None:
        """잘못된 인증 정보 시 401."""
        with patch(
            "src.api.routes.auth.AuthService.login",
            new_callable=AsyncMock,
            side_effect=AuthenticationError(
                message="이메일 또는 비밀번호가 올바르지 않습니다.",
                details={"reason": "invalid_credentials"},
            ),
        ):
            response = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


class TestRefreshRoute:
    """POST /api/v1/auth/refresh 테스트."""

    @pytest.mark.asyncio
    async def test_refresh_success_200(self, unauth_client: AsyncClient) -> None:
        """유효한 refresh 토큰(쿠키)으로 200과 갱신 메시지 반환."""
        with patch(
            "src.api.routes.auth.AuthService.refresh",
            return_value={
                "access_token": "new_access",
                "refresh_token": "new_refresh",
            },
        ):
            response = await unauth_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "old_refresh_token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "토큰 갱신 성공"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_401(self, unauth_client: AsyncClient) -> None:
        """유효하지 않은 토큰 시 401."""
        with patch(
            "src.api.routes.auth.AuthService.refresh",
            side_effect=AuthenticationError(
                message="유효하지 않은 토큰입니다.",
                details={"reason": "invalid_token"},
            ),
        ):
            response = await unauth_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "invalid_token"},
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


class TestLogoutRoute:
    """POST /api/v1/auth/logout 테스트."""

    @pytest.mark.asyncio
    async def test_logout_success_200(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """로그아웃 성공 시 200."""
        from src.api.security.auth import TokenPayload

        mock_payload = TokenPayload(
            sub=str(test_user.id),
            role=test_user.role,
            exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc),
            jti="jti-123",
            token_type="access",
        )

        with (
            patch(
                "src.api.routes.auth.verify_token",
                return_value=mock_payload,
            ),
            patch(
                "src.api.routes.auth.blacklist_token",
                new_callable=AsyncMock,
            ),
        ):
            response = await route_client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "로그아웃" in data["message"]

    @pytest.mark.asyncio
    async def test_logout_no_auth_401(self, unauth_client: AsyncClient) -> None:
        """인증 없이 로그아웃 시 401."""
        response = await unauth_client.post("/api/v1/auth/logout")
        assert response.status_code == 401
