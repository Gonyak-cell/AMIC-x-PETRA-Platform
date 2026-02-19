"""deal-mgmt 테스트 공통 Fixture.

- SQLite in-memory DB (aiosqlite)
- JWT 인증 모킹
- get_db 의존성 오버라이드
"""

import os

# 앱 모듈 import 전에 환경 변수 설정
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEBUG", "true")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# SQLite에서 PostgreSQL 전용 타입 컴파일 지원
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.main import app
from app.models import Base

# ── Test DB engine (SQLite in-memory) ──────────────────────
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


# ── JWT mock ───────────────────────────────────────────────
MOCK_CLAIMS = JWTClaims(
    user_id="test-user-id",
    email="test@example.com",
    role="admin",
)


async def _override_get_jwt_claims() -> JWTClaims:
    return MOCK_CLAIMS


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


# ── 의존성 오버라이드 적용 ─────────────────────────────────
app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims
app.dependency_overrides[get_db] = _override_get_db


# ── Fixtures ───────────────────────────────────────────────
@pytest.fixture(autouse=True)
async def setup_database():
    """테스트마다 DB 테이블 생성/삭제 — 격리 보장."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """테스트용 ASGI HTTP 클라이언트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """테스트용 DB 세션 (서비스 레이어 직접 테스트)."""
    async with _test_session_factory() as session:
        yield session


@pytest.fixture
async def transaction_id(client: AsyncClient) -> str:
    """테스트용 트랜잭션 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "Test Transaction",
            "code_name": f"TEST-{id(client)}",
            "target_company_name": "테스트 기업",
            "client_name": "테스트 고객",
            "side": "SELL",
            "lead_advisor_email": "test@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]
