"""Integration 테스트용 conftest

팩토리 기반 seed fixture와 테스트용 DB를 오버라이드한 AsyncClient를 제공한다.
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
    create_test_deal,
    create_test_fund,
    create_test_fund_manager,
    create_test_news,
    create_test_reputation,
    create_test_user,
)


@pytest.fixture
async def integration_engine():
    """Integration 테스트용 SQLite async 엔진"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(integration_engine) -> AsyncGenerator[AsyncSession, None]:
    """Integration 테스트용 async DB 세션"""
    session_factory = async_sessionmaker(
        integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(integration_engine) -> AsyncGenerator[AsyncClient, None]:
    """get_db를 테스트 DB로 오버라이드한 AsyncClient"""
    session_factory = async_sessionmaker(
        integration_engine,
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


# ───────────────────── Seed Fixtures ─────────────────────


@pytest.fixture
async def seed_companies(db_session):
    """3개의 샘플 기업을 생성한다."""
    c1 = await create_test_company(db_session, corp_code="00100001", corp_name="테스트투자파트너스 주식회사")
    c2 = await create_test_company(
        db_session,
        corp_code="00100002",
        corp_name="한국벤처캐피탈 주식회사",
        jurir_no="1101112345678",
        stock_code="000002",
    )
    c3 = await create_test_company(
        db_session,
        corp_code="00100003",
        corp_name="서울투자증권 주식회사",
        jurir_no="1101113456789",
        stock_code="000003",
    )
    return [c1, c2, c3]


@pytest.fixture
async def seed_funds(db_session, seed_companies):
    """2개의 펀드와 FundManager를 생성한다."""
    companies = seed_companies
    f1 = await create_test_fund(
        db_session,
        fund_code="FUND-001",
        fund_name="테스트 블라인드 1호",
        company_id=companies[0].id,
        company_name=companies[0].corp_name,
    )
    f2 = await create_test_fund(
        db_session,
        fund_code="FUND-002",
        fund_name="한국벤처 프로젝트 2호",
        fund_type="project",
        company_id=companies[1].id,
        company_name=companies[1].corp_name,
    )
    m1 = await create_test_fund_manager(db_session, fund_id=f1.id, manager_name="김대표")
    m2 = await create_test_fund_manager(db_session, fund_id=f2.id, manager_name="이심사역", position="심사역")
    return [f1, f2], [m1, m2]


@pytest.fixture
async def seed_news(db_session, seed_companies):
    """5개의 뉴스 기사를 생성한다 (기업에 연결)."""
    companies = seed_companies
    articles = []
    for i in range(5):
        article = await create_test_news(
            db_session,
            title=f"테스트 뉴스 기사 {i + 1}",
            content=f"뉴스 본문 {i + 1}. 테스트투자파트너스가 성공적 엑시트를 달성했다.",
            url=f"https://platum.kr/archives/test-{i + 1}",
            company_id=companies[i % len(companies)].id,
            sentiment_score=0.3 + (i * 0.1),
            published_at=datetime.now(UTC) - timedelta(days=i),
        )
        articles.append(article)
    return articles


@pytest.fixture
async def seed_deals(db_session, seed_companies):
    """3개의 딜을 생성한다."""
    companies = seed_companies
    deals = []
    for i in range(3):
        deal = await create_test_deal(
            db_session,
            target_company=f"피투자회사{i + 1}",
            company_id=companies[0].id,
            sector=["ai_deeptech", "bio_health", "fintech"][i],
            round_stage=["seed", "series_a", "series_b"][i],
            deal_date=datetime(2025, 6, 15 - i).date(),
            deal_year=2025,
        )
        deals.append(deal)
    return deals


@pytest.fixture
async def seed_user(db_session):
    """admin과 analyst 사용자를 생성한다."""
    admin = await create_test_user(
        db_session,
        username="admin_user",
        email="admin@kiis.io",
        password="adminpass123",
        role="admin",
    )
    analyst = await create_test_user(
        db_session,
        username="analyst_user",
        email="analyst@kiis.io",
        password="analystpass123",
        role="analyst",
    )
    return {"admin": admin, "analyst": analyst}


@pytest.fixture
async def auth_headers(client, seed_user):
    """로그인하여 Authorization 헤더를 반환한다."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_user", "password": "adminpass123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seed_reputation(db_session, seed_companies):
    """샘플 기업에 평판 점수를 생성한다."""
    companies = seed_companies
    rep = await create_test_reputation(db_session, company_id=companies[0].id)
    return rep
