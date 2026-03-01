"""get_jwt_claims 단위 테스트 — 4개 분기 커버.

1. AUTH_ENABLED=False → _DEV_CLAIMS 반환 + request.state.user_id 설정
2. 토큰 없음 (헤더+쿠키 모두) → 401
3. 유효한 토큰 → JWTClaims 반환 + request.state.user_id 설정
4. 만료된/잘못된 토큰 → 401
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTH_ENABLED"] = "true"
os.environ["JWT_SECRET"] = "test-jwt-secret-key"
os.environ["SECRET_KEY"] = "test-secret-key"

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _override_get_db():
    async with _test_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def setup_database():
    """테스트마다 DB 생성/삭제 + DB 오버라이드 적용."""
    app.dependency_overrides[get_db] = _override_get_db
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncClient:
    """테스트용 HTTP 클라이언트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _make_token(
    *,
    expired: bool = False,
    sub: str = "test-user-id",
    email: str = "test@example.com",
    role: str = "analyst",
) -> str:
    """테스트용 JWT 토큰 생성."""
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "exp": datetime.now(UTC) + (timedelta(hours=-1) if expired else timedelta(hours=1)),
    }
    return jwt.encode(payload, "test-jwt-secret-key", algorithm="HS256")


class TestGetJwtClaimsAuthEnabled:
    """AUTH_ENABLED=True 상태에서 get_jwt_claims 동작 검증."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_claims(self, client: AsyncClient) -> None:
        """유효한 JWT 토큰으로 대시보드 접근 시 200을 반환한다."""
        token = _make_token(email="analyst@kiis.io", role="analyst")
        resp = await client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        """토큰 없이 대시보드 접근 시 401을 반환한다."""
        resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        """잘못된 JWT 토큰으로 대시보드 접근 시 401을 반환한다."""
        resp = await client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client: AsyncClient) -> None:
        """만료된 JWT 토큰으로 대시보드 접근 시 401을 반환한다."""
        token = _make_token(expired=True)
        resp = await client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_cookie_fallback(self, client: AsyncClient) -> None:
        """Authorization 헤더 없이 쿠키로 토큰 전달 시 200을 반환한다."""
        token = _make_token()
        resp = await client.get(
            "/api/v1/dashboard/summary",
            cookies={"access_token": token},
        )
        assert resp.status_code == 200


class TestGetJwtClaimsDevMode:
    """AUTH_ENABLED=False 상태에서 get_jwt_claims 동작 검증."""

    @pytest.mark.asyncio
    async def test_dev_mode_returns_200_without_token(self, client: AsyncClient) -> None:
        """Dev 모드에서는 토큰 없이도 대시보드에 접근할 수 있다."""
        with patch("app.core.security.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = False
            mock_settings.JWT_SECRET = "test-jwt-secret-key"
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dev_mode_returns_dev_claims_data(self, client: AsyncClient) -> None:
        """Dev 모드에서 대시보드 응답이 올바른 구조를 가진다."""
        with patch("app.core.security.settings") as mock_settings:
            mock_settings.AUTH_ENABLED = False
            mock_settings.JWT_SECRET = "test-jwt-secret-key"
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "counts" in data
        assert "recent_deals" in data
