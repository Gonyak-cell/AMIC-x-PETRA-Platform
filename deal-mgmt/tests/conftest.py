"""deal-mgmt 테스트 공통 Fixture.

- SQLite in-memory DB (aiosqlite)
- JWT 인증 모킹
- get_db 의존성 오버라이드
- Celery 태스크 mock (Redis 불필요)
- --update-golden CLI 옵션
"""

import os
import sys
from types import ModuleType
from unittest.mock import MagicMock

# 앱 모듈 import 전에 환경 변수 설정
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_RESULT_BACKEND", "redis://localhost:6379/1")

# ── Celery mock (celery 패키지 미설치 환경 대응) ──────────
# celery를 import하기 전에 가짜 모듈 주입 → celery_app.py가 정상 로딩됨
# 태스크의 .delay()는 no-op MagicMock으로 대체
if "celery" not in sys.modules:
    _celery_mock = ModuleType("celery")

    class _FakeCelery:
        """Celery 미설치 환경에서 테스트용 가짜 Celery."""

        def __init__(self, *a, **kw):
            self.conf = MagicMock()

        def autodiscover_tasks(self, *a, **kw):
            pass

        def task(self, *a, **kw):
            """@celery_app.task 데코레이터 — 원본 함수를 그대로 반환 + .delay = no-op."""

            def decorator(fn):
                fn.delay = MagicMock(name=f"{fn.__name__}.delay")
                fn.apply_async = MagicMock(name=f"{fn.__name__}.apply_async")
                fn.s = MagicMock(name=f"{fn.__name__}.s")
                return fn

            if len(a) == 1 and callable(a[0]) and not kw:
                return decorator(a[0])
            return decorator

    _celery_mock.Celery = _FakeCelery  # type: ignore[attr-defined]
    sys.modules["celery"] = _celery_mock

    # celery.schedules 서브모듈 mock (cleanup_tasks.py의 crontab import 대응)
    _celery_schedules = ModuleType("celery.schedules")
    _celery_schedules.crontab = MagicMock(name="crontab")  # type: ignore[attr-defined]
    sys.modules["celery.schedules"] = _celery_schedules

from collections.abc import AsyncGenerator

import pytest

# ── --update-golden CLI 옵션 ──────────────────────────────────────


def pytest_addoption(parser):
    """커스텀 pytest CLI 옵션 등록."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="골든 파일을 현재 출력으로 업데이트 (비교 대신 덮어쓰기)",
    )


def pytest_configure(config):
    """마커 등록."""
    config.addinivalue_line("markers", "golden: 골든 파일 스냅샷 테스트")


from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

# SQLite에서 PostgreSQL 전용 타입 컴파일 지원
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(36)"

from app.core.database import get_db
from app.core.dependencies import get_fdd_client, get_im_client, get_kiis_client
from app.core.security import JWTClaims, get_jwt_claims
from app.main import app
from app.models import Base
from app.services.mock_clients import MockFDDClient, MockIMClient, MockKIISClient

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


@event.listens_for(_test_engine.sync_engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    """SQLite에서 CASCADE 삭제가 동작하도록 외래키 강제 활성화."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ── JWT mock ───────────────────────────────────────────────
MOCK_CLAIMS = JWTClaims(
    user_id="test-user-id",
    email="test@example.com",
    role="ADMIN",
)


async def _override_get_jwt_claims() -> JWTClaims:
    return MOCK_CLAIMS


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


# ── 의존성 오버라이드 적용 ─────────────────────────────────
app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims
app.dependency_overrides[get_db] = _override_get_db
app.dependency_overrides[get_kiis_client] = MockKIISClient
app.dependency_overrides[get_fdd_client] = MockFDDClient
app.dependency_overrides[get_im_client] = MockIMClient


# ── Fixtures ───────────────────────────────────────────────
@pytest.fixture(autouse=True)
async def setup_database():
    """테스트마다 DB 테이블 생성/삭제 — 격리 보장."""
    # GP 프로필 캐시 리셋 (fi_mapping_service 모듈 레벨 캐시)
    from app.services import fi_mapping_service

    fi_mapping_service._gp_cache = None
    fi_mapping_service._gp_cache_ts = 0.0

    # Rate limit 상태 리셋 (테스트 간 429 방지)
    from app.core.rate_limiter import fi_rate_limiter, si_rate_limiter

    fi_rate_limiter.clear()
    si_rate_limiter.clear()

    # VDR 업로드 Rate limiter 리셋
    from app.routers.vdr import _upload_limiter

    _upload_limiter.clear()

    # BackgroundTasks용 async_session_factory를 테스트 DB로 교체
    import app.core.database as _db_module

    _db_module.async_session_factory = _test_session_factory

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


def make_claims(
    role: str = "ADMIN",
    email: str = "test@example.com",
    user_id: str = "test-user-id",
) -> JWTClaims:
    """역할별 JWT Claims 팩토리 — 테스트에서 RBAC 검증용."""
    return JWTClaims(user_id=user_id, email=email, role=role)


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
            "deal_type": "SE",
            "target_company_name": "테스트 기업",
            "client_name": "테스트 고객",
            "side": "SELL",
            "lead_advisor_email": "test@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def sample_transaction(client: AsyncClient) -> dict:
    """마케팅 자료 테스트용 거래 생성 (dict 반환)."""
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "마케팅자료 테스트 거래",
            "deal_type": "SE",
            "side": "SELL",
            "target_company_name": "테스트 대상기업",
            "client_name": "테스트 의뢰기업",
            "lead_advisor_email": "advisor@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def another_transaction(client: AsyncClient) -> dict:
    """격리 테스트용 두 번째 거래 (dict 반환)."""
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "격리 테스트 거래",
            "deal_type": "SE",
            "side": "BUY",
            "target_company_name": "격리 대상기업",
            "client_name": "격리 의뢰기업",
            "lead_advisor_email": "advisor2@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()
