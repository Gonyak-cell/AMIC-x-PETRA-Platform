"""인증 가드 통합 테스트 — JWT 오버라이드 없이 실제 검증.

conftest.py의 get_jwt_claims override를 이 모듈에서만 제거하여
실제 JWT 검증 로직을 테스트한다. 이 테스트가 통과하면
코드 수정 후 인증 관련 회귀 오류가 방지된다.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

from app.core.database import get_db
from app.core.security import get_jwt_claims
from app.main import app
from app.models import Base

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    poolclass=StaticPool,
)
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
    """테스트마다 DB 생성/삭제 + 인증 오버라이드 일시 제거/복원."""
    # 기존 오버라이드 백업
    original_db = app.dependency_overrides.get(get_db)
    original_auth = app.dependency_overrides.pop(get_jwt_claims, None)

    # 이 모듈 전용 DB 오버라이드 적용
    app.dependency_overrides[get_db] = _override_get_db

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # 오버라이드 복원 (다른 테스트 파일에 영향 방지)
    if original_auth is not None:
        app.dependency_overrides[get_jwt_claims] = original_auth
    if original_db is not None:
        app.dependency_overrides[get_db] = original_db
    else:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def unauthenticated_client():
    """인증 오버라이드가 없는 클라이언트 — 실제 JWT 검증."""
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
    async def test_transactions_requires_auth(self, unauthenticated_client):
        resp = await unauthenticated_client.get("/api/v1/transactions")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_transaction_requires_auth(self, unauthenticated_client):
        resp = await unauthenticated_client.post(
            "/api/v1/transactions",
            json={
                "name": "Test",
                "code_name": "TST-001",
                "side": "SELL",
                "target_company_name": "Target",
                "client_name": "Client",
                "lead_advisor_email": "test@test.com",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self, unauthenticated_client):
        resp = await unauthenticated_client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {_make_token(valid=False)}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_jwt_returns_401(self, unauthenticated_client):
        resp = await unauthenticated_client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {_make_token(expired=True)}"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_health_does_not_require_auth(self, unauthenticated_client):
        resp = await unauthenticated_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_valid_jwt_header_auth(self, unauthenticated_client):
        """유효한 JWT로 인증이 통과해야 한다."""
        resp = await unauthenticated_client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_valid_jwt_cookie_auth(self, unauthenticated_client):
        """쿠키를 통한 JWT 인증도 작동해야 한다."""
        resp = await unauthenticated_client.get(
            "/api/v1/transactions",
            cookies={"access_token": _make_token()},
        )
        assert resp.status_code == 200
