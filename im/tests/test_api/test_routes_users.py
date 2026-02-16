"""사용자 라우트 테스트 (test_routes_users.py).

> 마지막 수정: 2026-02-10 19:30:00

GET/PATCH /api/v1/users/me, POST/GET/PATCH/DELETE /api/v1/users 엔드포인트 검증.
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
from src.api.exceptions import NotFoundError


def _make_user(
    role: str = "USER",
    user_id: uuid.UUID | None = None,
    email: str = "test@example.com",
    full_name: str = "Test User",
) -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.is_active = True
    user.email = email
    user.full_name = full_name
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def regular_user() -> MagicMock:
    return _make_user(role="USER")


@pytest.fixture
def admin_user() -> MagicMock:
    return _make_user(role="ADMIN")


@pytest.fixture
def user_app(regular_user):
    """일반 사용자 앱."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: regular_user
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    return app


@pytest.fixture
async def user_client(user_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=user_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def admin_app(admin_user):
    """관리자 앱."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    return app


@pytest.fixture
async def admin_client(admin_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=admin_app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# GET /api/v1/users/me
# ---------------------------------------------------------------------------


class TestGetMe:
    """GET /api/v1/users/me 테스트."""

    @pytest.mark.asyncio
    async def test_get_me_200(
        self, user_client: AsyncClient, regular_user: MagicMock
    ) -> None:
        """내 프로필 조회 시 200."""
        response = await user_client.get("/api/v1/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == regular_user.email
        assert data["role"] == regular_user.role


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/me
# ---------------------------------------------------------------------------


class TestUpdateMe:
    """PATCH /api/v1/users/me 테스트."""

    @pytest.mark.asyncio
    async def test_update_me_200(
        self, user_client: AsyncClient, regular_user: MagicMock
    ) -> None:
        """프로필 수정 시 200."""
        updated_user = _make_user(
            role=regular_user.role,
            user_id=regular_user.id,
            email=regular_user.email,
            full_name="Updated Name",
        )

        with patch(
            "src.api.routes.users.UserService.update_me",
            new_callable=AsyncMock,
            return_value=updated_user,
        ):
            response = await user_client.patch(
                "/api/v1/users/me",
                json={"full_name": "Updated Name"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"


# ---------------------------------------------------------------------------
# POST /api/v1/users
# ---------------------------------------------------------------------------


class TestCreateUser:
    """POST /api/v1/users 테스트."""

    @pytest.mark.asyncio
    async def test_create_user_admin_201(
        self, admin_client: AsyncClient, admin_user: MagicMock
    ) -> None:
        """ADMIN이 사용자 생성 시 201."""
        new_user = _make_user(
            email="newuser@example.com",
            full_name="New User",
        )

        with patch(
            "src.api.routes.users.UserService.create_user",
            new_callable=AsyncMock,
            return_value=new_user,
        ):
            response = await admin_client.post(
                "/api/v1/users",
                json={
                    "email": "newuser@example.com",
                    "password": "password123",
                    "full_name": "New User",
                    "role": "USER",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_create_user_non_admin_403(
        self, user_client: AsyncClient
    ) -> None:
        """일반 사용자가 사용자 생성 시 403."""
        response = await user_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User",
                "role": "USER",
            },
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/v1/users
# ---------------------------------------------------------------------------


class TestListUsers:
    """GET /api/v1/users 테스트."""

    @pytest.mark.asyncio
    async def test_list_users_admin_200(
        self, admin_client: AsyncClient
    ) -> None:
        """ADMIN이 사용자 목록 조회 시 200."""
        users = [_make_user() for _ in range(3)]

        with patch(
            "src.api.routes.users.UserService.list_users",
            new_callable=AsyncMock,
            return_value=(users, 3),
        ):
            response = await admin_client.get(
                "/api/v1/users?offset=0&limit=10"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_users_non_admin_403(
        self, user_client: AsyncClient
    ) -> None:
        """일반 사용자가 목록 조회 시 403."""
        response = await user_client.get("/api/v1/users")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/v1/users/{user_id}
# ---------------------------------------------------------------------------


class TestGetUser:
    """GET /api/v1/users/{user_id} 테스트."""

    @pytest.mark.asyncio
    async def test_get_user_admin_200(
        self, admin_client: AsyncClient
    ) -> None:
        """ADMIN이 특정 사용자 조회 시 200."""
        target_user = _make_user(email="target@example.com")

        with patch(
            "src.api.routes.users.UserService.get_by_id",
            new_callable=AsyncMock,
            return_value=target_user,
        ):
            response = await admin_client.get(
                f"/api/v1/users/{target_user.id}"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "target@example.com"


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/{user_id}
# ---------------------------------------------------------------------------


class TestAdminUpdateUser:
    """PATCH /api/v1/users/{user_id} 테스트."""

    @pytest.mark.asyncio
    async def test_admin_update_user_200(
        self, admin_client: AsyncClient
    ) -> None:
        """ADMIN이 사용자 수정 시 200."""
        target_id = uuid.uuid4()
        updated_user = _make_user(
            user_id=target_id,
            role="MANAGER",
        )

        with patch(
            "src.api.routes.users.UserService.admin_update",
            new_callable=AsyncMock,
            return_value=updated_user,
        ):
            response = await admin_client.patch(
                f"/api/v1/users/{target_id}",
                json={"role": "MANAGER"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "MANAGER"


# ---------------------------------------------------------------------------
# DELETE /api/v1/users/{user_id}
# ---------------------------------------------------------------------------


class TestDeactivateUser:
    """DELETE /api/v1/users/{user_id} 테스트."""

    @pytest.mark.asyncio
    async def test_deactivate_user_admin_204(
        self, admin_client: AsyncClient
    ) -> None:
        """ADMIN이 사용자 비활성화 시 204."""
        target_id = uuid.uuid4()

        with patch(
            "src.api.routes.users.UserService.deactivate",
            new_callable=AsyncMock,
        ):
            response = await admin_client.delete(
                f"/api/v1/users/{target_id}"
            )

        assert response.status_code == 204
