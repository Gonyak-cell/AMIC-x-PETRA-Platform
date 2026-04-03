"""Authentication guard integration tests using real JWT validation."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

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
    """Create an isolated test DB and temporarily remove JWT override."""
    import app.core.database as database_module

    original_db = app.dependency_overrides.get(get_db)
    original_auth = app.dependency_overrides.pop(get_jwt_claims, None)
    original_session_factory = database_module.async_session_factory

    app.dependency_overrides[get_db] = _override_get_db
    database_module.async_session_factory = _test_session_factory

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    database_module.async_session_factory = original_session_factory
    if original_auth is not None:
        app.dependency_overrides[get_jwt_claims] = original_auth
    if original_db is not None:
        app.dependency_overrides[get_db] = original_db
    else:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def unauthenticated_client():
    """Client with real JWT validation enabled."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


def _make_token(*, expired: bool = False, valid: bool = True) -> str:
    """Create a test JWT token."""
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
    """Verify protected endpoints reject missing or invalid auth."""

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
                "deal_type": "SE",
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
        resp = await unauthenticated_client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {_make_token()}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_valid_jwt_cookie_auth(self, unauthenticated_client):
        resp = await unauthenticated_client.get(
            "/api/v1/transactions",
            cookies={"access_token": _make_token()},
        )
        assert resp.status_code == 200
