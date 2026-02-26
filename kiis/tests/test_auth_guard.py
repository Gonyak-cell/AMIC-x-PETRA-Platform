"""인증 가드 통합 테스트 — AUTH_ENABLED=True 상태에서 실제 JWT 검증.

conftest.py의 client fixture를 사용하되, AUTH_ENABLED=True로 설정하여
인증이 필요한 엔드포인트가 토큰 없이 401을 반환하는지 검증한다.
이 테스트가 통과하면 코드 수정 후 인증 관련 회귀 오류가 방지된다.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTH_ENABLED"] = "true"
os.environ["JWT_SECRET"] = "test-jwt-secret-key"
os.environ["SECRET_KEY"] = "test-secret-key"

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)
_test_session_factory = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False,
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


@pytest.fixture
async def unauthenticated_client():
    """인증 없는 클라이언트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _make_token(*, expired: bool = False, valid: bool = True) -> str:
    """테스트용 JWT 토큰 생성."""
    if not valid:
        return "invalid.jwt.token"
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "role": "admin",
        "exp": datetime.now(UTC) + (timedelta(hours=-1) if expired else timedelta(hours=1)),
    }
    return jwt.encode(payload, "test-jwt-secret-key", algorithm="HS256")


class TestAuthGuard:
    """인증이 필요한 엔드포인트가 토큰 없이 401을 반환하는지 검증."""

    @pytest.mark.asyncio
    async def test_watchlist_requires_auth(self, unauthenticated_client):
        """워치리스트 조회에 인증이 필요하다."""
        resp = await unauthenticated_client.get("/api/v1/watchlist")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_alerts_requires_auth(self, unauthenticated_client):
        """알림 조회에 인증이 필요하다."""
        resp = await unauthenticated_client.get("/api/v1/alerts")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_alerts_unread_count_requires_auth(self, unauthenticated_client):
        """안 읽은 알림 수 조회에 인증이 필요하다."""
        resp = await unauthenticated_client.get("/api/v1/alerts/unread-count")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self, unauthenticated_client):
        """잘못된 JWT로 401을 반환한다."""
        resp = await unauthenticated_client.get(
            "/api/v1/watchlist",
            headers={"Authorization": f"Bearer {_make_token(valid=False)}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_jwt_returns_401(self, unauthenticated_client):
        """만료된 JWT로 401을 반환한다."""
        resp = await unauthenticated_client.get(
            "/api/v1/watchlist",
            headers={"Authorization": f"Bearer {_make_token(expired=True)}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_health_does_not_require_auth(self, unauthenticated_client):
        """/health는 인증이 필요하지 않다."""
        resp = await unauthenticated_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "degraded")

    @pytest.mark.asyncio
    async def test_deals_does_not_require_auth(self, unauthenticated_client):
        """딜 목록은 인증 없이 접근 가능하다 (public API)."""
        resp = await unauthenticated_client.get("/api/v1/deals")
        # 200 또는 422(파라미터 필요) — 401이 아닌 것이 중요
        assert resp.status_code != 401
