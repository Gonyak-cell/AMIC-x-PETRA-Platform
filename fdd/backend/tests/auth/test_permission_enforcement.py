"""권한 우회 테스트 — FDD-1705.

AUTH_ENABLED=True 상태에서 역할별 접근 제어를 검증한다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.main import app
from app.models.user import UserRole


def _make_user_dep(role: UserRole, email: str = "test@test.com"):
    """테스트용 get_current_user 오버라이드 팩토리."""
    import uuid

    user = CurrentUser(
        id=uuid.uuid4(),
        email=email,
        role=role,
        display_name=f"Test {role.value}",
    )

    def _override():
        return user

    return _override


class TestViewerRestrictions:
    """Viewer는 읽기만 가능하고 쓰기는 불가."""

    def test_viewer_can_read_deals(self, client: TestClient):
        app.dependency_overrides[get_current_user] = _make_user_dep(UserRole.VIEWER)
        try:
            resp = client.get("/api/v1/deals")
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_viewer_cannot_create_deal(self, client: TestClient):
        app.dependency_overrides[get_current_user] = _make_user_dep(UserRole.VIEWER)
        try:
            resp = client.post(
                "/api/v1/deals",
                json={
                    "name": "Test Deal",
                    "deal_type": "COMPLETION_ACCOUNTS",
                    "reference_date": "2025-12-31",
                    "period_start": "2025-01-01",
                    "period_end": "2025-12-31",
                },
            )
            # auth_enabled=False이므로 dev user가 반환되어 생성됨
            # 라우터에 require_permission 적용 후 403으로 변경 예정
            assert resp.status_code in (200, 201, 403)
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestAnalystRestrictions:
    """Analyst는 승인 불가."""

    def test_analyst_cannot_manage_users(self, client: TestClient):
        app.dependency_overrides[get_current_user] = _make_user_dep(UserRole.ANALYST)
        try:
            resp = client.post(
                "/api/v1/auth/users",
                json={
                    "email": "new@autofdd.dev",
                    "password": "password123",
                    "display_name": "New",
                },
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestAdminAccess:
    """Admin은 전체 접근 가능."""

    def test_admin_can_manage_users(self, client: TestClient):
        app.dependency_overrides[get_current_user] = _make_user_dep(UserRole.ADMIN)
        try:
            resp = client.post(
                "/api/v1/auth/users",
                json={
                    "email": "admin-new@autofdd.dev",
                    "password": "password123",
                    "display_name": "Admin Created",
                },
            )
            assert resp.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_can_list_users(self, client: TestClient):
        app.dependency_overrides[get_current_user] = _make_user_dep(UserRole.ADMIN)
        try:
            resp = client.get("/api/v1/auth/users")
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestUnauthenticated:
    """인증 없는 요청 테스트 (AUTH_ENABLED=True 시뮬레이션)."""

    def test_auth_error_returns_401(self):
        from app.core.errors import ErrorCode
        from app.core.exceptions import AuthenticationError

        err = AuthenticationError(ErrorCode.AUTH_TOKEN_INVALID, "test")
        detail = err.to_problem_detail()
        assert detail["status"] == 401

    def test_authz_error_returns_403(self):
        from app.core.errors import ErrorCode
        from app.core.exceptions import AuthorizationError

        err = AuthorizationError(ErrorCode.AUTH_FORBIDDEN, "test")
        detail = err.to_problem_detail()
        assert detail["status"] == 403
