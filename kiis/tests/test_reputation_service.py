"""평판 스코어링 서비스 테스트"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.news import NewsArticle
from app.models.reputation import ReputationHistory
from app.services.reputation_service import ReputationService


@pytest.fixture
def reputation_service() -> ReputationService:
    """평판 서비스 인스턴스"""
    return ReputationService()


@pytest.fixture
async def sample_company(async_session: AsyncSession) -> Company:
    """테스트용 기업"""
    company = Company(
        corp_code="00100001",
        corp_name="한국투자파트너스 주식회사",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def sample_news_positive(async_session: AsyncSession, sample_company: Company) -> list[NewsArticle]:
    """긍정 뉴스 샘플"""
    now = datetime.now(UTC)
    articles = [
        NewsArticle(
            title="한국투자파트너스, 대규모 펀드 결성 성공",
            content="성공적인 펀드레이징을 완료했다.",
            source="platum",
            url=f"https://example.com/news/{i}",
            url_hash=NewsArticle.generate_url_hash(f"https://example.com/news/{i}"),
            published_at=now - timedelta(days=i * 10),
            sentiment_score=0.7,
            company_id=sample_company.id,
        )
        for i in range(3)
    ]
    async_session.add_all(articles)
    await async_session.flush()
    return articles


@pytest.fixture
async def sample_news_negative(async_session: AsyncSession, sample_company: Company) -> list[NewsArticle]:
    """부정 뉴스 샘플"""
    now = datetime.now(UTC)
    articles = [
        NewsArticle(
            title="한국투자파트너스, 운용 인력 이탈",
            content="핵심 인력이 퇴사했다.",
            source="dealsite",
            url=f"https://example.com/news/neg/{i}",
            url_hash=NewsArticle.generate_url_hash(f"https://example.com/news/neg/{i}"),
            published_at=now - timedelta(days=i * 10),
            sentiment_score=-0.6,
            company_id=sample_company.id,
        )
        for i in range(3)
    ]
    async_session.add_all(articles)
    await async_session.flush()
    return articles


@pytest.fixture
async def sample_news_exit(async_session: AsyncSession, sample_company: Company) -> list[NewsArticle]:
    """엑시트 뉴스 샘플"""
    now = datetime.now(UTC)
    articles = [
        NewsArticle(
            title="한국투자파트너스 피투자사, IPO 성공",
            content="성공적 엑시트를 달성했다. 상장 완료.",
            source="platum",
            url="https://example.com/news/exit/1",
            url_hash=NewsArticle.generate_url_hash("https://example.com/news/exit/1"),
            published_at=now - timedelta(days=30),
            sentiment_score=0.8,
            company_id=sample_company.id,
        ),
        NewsArticle(
            title="한국투자파트너스 M&A 딜 성사",
            content="인수 계약이 체결되었다.",
            source="dealsite",
            url="https://example.com/news/exit/2",
            url_hash=NewsArticle.generate_url_hash("https://example.com/news/exit/2"),
            published_at=now - timedelta(days=60),
            sentiment_score=0.7,
            company_id=sample_company.id,
        ),
    ]
    async_session.add_all(articles)
    await async_session.flush()
    return articles


class TestNormalizeNewsScore:
    """뉴스 점수 정규화 테스트"""

    def test_normalize_positive(self, reputation_service: ReputationService):
        """긍정 점수 정규화"""
        result = reputation_service._normalize_news_score(Decimal("0.5"))
        assert result == Decimal("0.75")

    def test_normalize_negative(self, reputation_service: ReputationService):
        """부정 점수 정규화"""
        result = reputation_service._normalize_news_score(Decimal("-0.5"))
        assert result == Decimal("0.25")

    def test_normalize_zero(self, reputation_service: ReputationService):
        """중립 점수 정규화"""
        result = reputation_service._normalize_news_score(Decimal("0"))
        assert result == Decimal("0.5")

    def test_normalize_max(self, reputation_service: ReputationService):
        """최대 점수 정규화"""
        result = reputation_service._normalize_news_score(Decimal("1.0"))
        assert result == Decimal("1.0")

    def test_normalize_min(self, reputation_service: ReputationService):
        """최소 점수 정규화"""
        result = reputation_service._normalize_news_score(Decimal("-1.0"))
        assert result == Decimal("0.0")


class TestDetermineStatusTag:
    """상태 태그 결정 테스트"""

    def test_status_rising(self, reputation_service: ReputationService):
        """Rising 조건: total >= 0.7 AND trend >= 0.6"""
        result = reputation_service._determine_status_tag(Decimal("0.75"), Decimal("0.65"))
        assert result == "rising"

    def test_status_risk(self, reputation_service: ReputationService):
        """Risk 조건: total < 0.4"""
        result = reputation_service._determine_status_tag(Decimal("0.35"), Decimal("0.5"))
        assert result == "risk"

    def test_status_stable_default(self, reputation_service: ReputationService):
        """Stable 조건: 기타"""
        result = reputation_service._determine_status_tag(Decimal("0.5"), Decimal("0.5"))
        assert result == "stable"

    def test_status_stable_high_total_low_trend(self, reputation_service: ReputationService):
        """Stable: total 높지만 trend 낮음"""
        result = reputation_service._determine_status_tag(Decimal("0.8"), Decimal("0.3"))
        assert result == "stable"


class TestCalculateNewsScore:
    """뉴스 점수 계산 테스트"""

    async def test_with_positive_news(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_positive: list[NewsArticle],
    ):
        """긍정 뉴스 평균"""
        score, count = await reputation_service._calculate_news_score(async_session, sample_company.id, months=6)
        assert count == 3
        assert score > Decimal("0.5")

    async def test_with_negative_news(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_negative: list[NewsArticle],
    ):
        """부정 뉴스 평균"""
        score, count = await reputation_service._calculate_news_score(async_session, sample_company.id, months=6)
        assert count == 3
        assert score < Decimal("0")

    async def test_no_news(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
    ):
        """뉴스 없음"""
        score, count = await reputation_service._calculate_news_score(async_session, sample_company.id, months=6)
        assert count == 0
        assert score == Decimal("0")


class TestCalculatePerformanceScore:
    """성과 점수 계산 테스트"""

    async def test_with_exit_news(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_exit: list[NewsArticle],
    ):
        """엑시트 뉴스 있는 경우"""
        score, exit_count = await reputation_service._calculate_performance_score(
            async_session, sample_company.id, months=12
        )
        assert exit_count >= 1
        assert score > Decimal("0")

    async def test_no_exit_news(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
    ):
        """엑시트 뉴스 없는 경우"""
        score, exit_count = await reputation_service._calculate_performance_score(
            async_session, sample_company.id, months=12
        )
        assert exit_count == 0
        assert score == Decimal("0")


class TestCalculateReputation:
    """평판 계산 통합 테스트"""

    async def test_calculate_basic(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_positive: list[NewsArticle],
    ):
        """기본 평판 계산"""
        reputation = await reputation_service.calculate_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
            months=6,
            save_history=True,
        )

        assert reputation is not None
        assert reputation.company_id == sample_company.id
        assert reputation.status_tag in ("rising", "stable", "risk")
        assert Decimal("0") <= reputation.total_score <= Decimal("1")
        assert reputation.news_count == 3

    async def test_calculate_no_company(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
    ):
        """존재하지 않는 기업"""
        reputation = await reputation_service.calculate_reputation(
            db=async_session,
            corp_code="99999999",
            months=6,
        )
        assert reputation is None

    async def test_calculate_updates_existing(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_positive: list[NewsArticle],
    ):
        """기존 평판 업데이트"""
        # 첫 번째 계산
        rep1 = await reputation_service.calculate_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
            months=6,
            save_history=False,
        )

        # 두 번째 계산
        rep2 = await reputation_service.calculate_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
            months=6,
            save_history=False,
        )

        assert rep1.id == rep2.id  # 동일 레코드 업데이트


class TestGetReputation:
    """평판 조회 테스트"""

    async def test_get_existing(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_positive: list[NewsArticle],
    ):
        """존재하는 평판 조회"""
        # 먼저 계산
        await reputation_service.calculate_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
            months=6,
        )

        # 조회
        reputation = await reputation_service.get_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
        )

        assert reputation is not None
        assert reputation.company_id == sample_company.id

    async def test_get_nonexistent(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
    ):
        """존재하지 않는 평판 조회"""
        reputation = await reputation_service.get_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
        )
        assert reputation is None


class TestReputationHistory:
    """평판 이력 테스트"""

    async def test_save_history(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_positive: list[NewsArticle],
    ):
        """이력 저장"""
        await reputation_service.calculate_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
            months=6,
            save_history=True,
        )

        # 이력 확인
        stmt = select(ReputationHistory).where(ReputationHistory.company_id == sample_company.id)
        result = await async_session.execute(stmt)
        history = result.scalars().all()

        assert len(history) >= 1

    async def test_get_history(
        self,
        async_session: AsyncSession,
        reputation_service: ReputationService,
        sample_company: Company,
        sample_news_positive: list[NewsArticle],
    ):
        """이력 조회"""
        # 여러 번 계산하여 이력 생성
        await reputation_service.calculate_reputation(
            db=async_session,
            corp_code=sample_company.corp_code,
            months=6,
            save_history=True,
        )

        history = await reputation_service.get_reputation_history(
            db=async_session,
            corp_code=sample_company.corp_code,
            limit=10,
        )

        assert len(history) >= 1
        assert history[0].company_id == sample_company.id
