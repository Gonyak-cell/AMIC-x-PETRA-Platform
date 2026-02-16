"""E2E 테스트용 conftest

Integration conftest와 동일한 DB/클라이언트 설정을 사용한다.
pytest의 conftest 상속을 통해 tests/integration/conftest.py의 fixture를 재사용할 수도 있지만,
E2E 테스트는 독립적으로 실행될 수 있도록 자체 fixture를 정의한다.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base
from tests.factories import (
    create_test_company,
    create_test_company_alias,
    create_test_deal,
    create_test_news,
)


@pytest.fixture
async def e2e_engine():
    """E2E 테스트용 SQLite async 엔진"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(e2e_engine) -> AsyncGenerator[AsyncSession, None]:
    """E2E 테스트용 async DB 세션"""
    session_factory = async_sessionmaker(
        e2e_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(e2e_engine) -> AsyncGenerator[AsyncClient, None]:
    """get_db를 테스트 DB로 오버라이드한 AsyncClient"""
    session_factory = async_sessionmaker(
        e2e_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ───────────────────── E2E Seed Fixtures ─────────────────────


@pytest.fixture
async def seed_e2e_data(db_session):
    """E2E 테스트에 필요한 전체 시드 데이터를 생성한다."""
    # Companies
    c1 = await create_test_company(db_session, corp_code="00200001", corp_name="이투스자산운용 주식회사")
    c2 = await create_test_company(
        db_session,
        corp_code="00200002",
        corp_name="그린벤처캐피탈 주식회사",
        jurir_no="2201112345678",
        stock_code="200002",
    )

    # Aliases
    alias1 = await create_test_company_alias(db_session, alias_name="이투스", company_id=c1.id)

    # News
    news_list = []
    for i in range(3):
        n = await create_test_news(
            db_session,
            title=f"E2E 테스트 뉴스 {i + 1}",
            url=f"https://e2e-test.com/news/{i + 1}",
            company_id=c1.id,
            sentiment_score=0.4 + (i * 0.1),
            published_at=datetime.now(UTC) - timedelta(days=i),
        )
        news_list.append(n)

    # Deals
    deals = []
    for i in range(2):
        d = await create_test_deal(
            db_session,
            target_company=f"E2E피투자사{i + 1}",
            company_id=c1.id,
            sector=["ai_deeptech", "fintech"][i],
            deal_date=datetime(2025, 7, 1 + i).date(),
        )
        deals.append(d)

    return {
        "companies": [c1, c2],
        "aliases": [alias1],
        "news": news_list,
        "deals": deals,
    }


@pytest.fixture
async def registered_user(client):
    """회원가입된 사용자 정보를 반환한다."""
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "e2e_testuser",
            "email": "e2e@kiis.io",
            "password": "e2epassword123",
        },
    )
    assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"
    return {
        "username": "e2e_testuser",
        "password": "e2epassword123",
        "user": reg_response.json(),
    }


@pytest.fixture
async def auth_headers(client, registered_user):
    """로그인하여 Authorization 헤더를 반환한다."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
