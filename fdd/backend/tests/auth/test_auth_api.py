"""인증 API 통합 테스트."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.config import settings
from app.models.user import User, UserRole


class TestLogin:
    def test_login_success(self, client: TestClient, test_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@autofdd.dev", "password": "testpassword123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == settings.access_token_expire_minutes * 60

    def test_login_wrong_password(self, client: TestClient, test_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@autofdd.dev", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@autofdd.dev", "password": "anything"},
        )
        assert resp.status_code == 401

    def test_login_disabled_user(self, client: TestClient, db: Session):
        user = User(
            email="disabled@autofdd.dev",
            hashed_password=hash_password("password123"),
            display_name="Disabled",
            role=UserRole.ANALYST,
            is_active=False,
        )
        db.add(user)
        db.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@autofdd.dev", "password": "password123"},
        )
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client: TestClient, test_user):
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@autofdd.dev", "password": "testpassword123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_with_invalid_token(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401


class TestGetMe:
    def test_get_me_with_auth_disabled(self, client: TestClient):
        """AUTH_ENABLED=False이면 dev 사용자를 반환한다."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "system@autofdd.dev"

    def test_get_me_with_valid_token(self, client: TestClient, auth_headers, test_user):
        """유효한 토큰으로 사용자 정보를 반환한다."""
        # auth_enabled=False이지만 get_current_user가 dev user를 반환함
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200


class TestUserManagement:
    def test_create_user_with_auth_disabled(self, client: TestClient):
        """AUTH_ENABLED=False이면 dev admin으로 사용자 생성 가능."""
        resp = client.post(
            "/api/v1/auth/users",
            json={
                "email": "new@autofdd.dev",
                "password": "newpassword123",
                "display_name": "New User",
                "role": "ANALYST",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "new@autofdd.dev"

    def test_list_users(self, client: TestClient, test_user):
        resp = client.get("/api/v1/auth/users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
