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
        assert data["message"] == "로그인 성공"
        # httpOnly 쿠키로 토큰 전달
        assert "access_token" in resp.cookies
        assert "refresh_token" in resp.cookies

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
        # 로그인하면 TestClient가 쿠키를 자동 저장
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@autofdd.dev", "password": "testpassword123"},
        )

        # refresh는 쿠키에서 refresh_token을 읽음
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        assert resp.json()["message"] == "토큰 갱신 성공"

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
