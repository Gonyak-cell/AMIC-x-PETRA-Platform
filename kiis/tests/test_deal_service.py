"""딜 소싱 서비스 테스트"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal, DealSector, DealStage
from app.models.news import NewsArticle
from app.services.deal_service import DealService


@pytest.fixture
def deal_service() -> DealService:
    """딜 서비스 인스턴스"""
    return DealService()


@pytest.fixture
async def sample_company(async_session: AsyncSession) -> Company:
    """테스트용 투자사"""
    company = Company(
        corp_code="00100001",
        corp_name="한국투자파트너스 주식회사",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def sample_deals(async_session: AsyncSession, sample_company: Company) -> list[Deal]:
    """테스트용 딜 데이터"""
    deals = [
        Deal(
            company_id=sample_company.id,
            target_company="AI스타트업",
            amount=Decimal("5000000000"),  # 50억
            amount_display="50억원",
            round_stage=DealStage.SERIES_A,
            sector=DealSector.AI_DEEPTECH,
            deal_date=date(2025, 6, 15),
            deal_year=2025,
            source_type="news",
        ),
        Deal(
            company_id=sample_company.id,
            target_company="바이오벤처",
            amount=Decimal("15000000000"),  # 150억
            amount_display="150억원",
            round_stage=DealStage.SERIES_B,
            sector=DealSector.BIO_HEALTH,
            deal_date=date(2025, 3, 10),
            deal_year=2025,
            source_type="news",
        ),
        Deal(
            company_id=sample_company.id,
            target_company="핀테크회사",
            amount=Decimal("3000000000"),  # 30억
            amount_display="30억원",
            round_stage=DealStage.SERIES_A,
            sector=DealSector.FINTECH,
            deal_date=date(2024, 11, 20),
            deal_year=2024,
            source_type="disclosure",
        ),
        Deal(
            company_id=sample_company.id,
            target_company="시드스타트업",
            amount=Decimal("500000000"),  # 5억
            amount_display="5억원",
            round_stage=DealStage.SEED,
            sector=DealSector.SAAS,
            deal_date=date(2024, 8, 5),
            deal_year=2024,
            source_type="manual",
        ),
    ]
    async_session.add_all(deals)
    await async_session.flush()
    return deals


@pytest.fixture
async def sample_news_with_investment(async_session: AsyncSession, sample_company: Company) -> NewsArticle:
    """투자 정보가 포함된 뉴스"""
    article = NewsArticle(
        title="AI스타트업, 시리즈A 100억원 투자 유치",
        content="한국투자파트너스 등이 참여하여 AI스타트업에 100억원 규모의 시리즈A 투자를 진행했다. "
        "2025년 6월 15일 계약이 체결되었다.",
        source="platum",
        url="https://example.com/news/investment/1",
        url_hash=NewsArticle.generate_url_hash("https://example.com/news/investment/1"),
        published_at=datetime.now(UTC),
        sentiment_score=0.6,
        company_id=sample_company.id,
    )
    async_session.add(article)
    await async_session.flush()
    return article


class TestClassifySector:
    """섹터 분류 테스트"""

    def test_classify_ai_sector(self, deal_service: DealService):
        """AI/딥테크 섹터 분류"""
        text = "인공지능 기반 자율주행 솔루션을 개발하는 스타트업"
        sector, keywords = deal_service.classify_sector(text)
        assert sector == DealSector.AI_DEEPTECH
        assert len(keywords) > 0

    def test_classify_bio_sector(self, deal_service: DealService):
        """바이오/헬스케어 섹터 분류"""
        text = "신약 개발 바이오 제약 회사"
        sector, keywords = deal_service.classify_sector(text)
        assert sector == DealSector.BIO_HEALTH

    def test_classify_saas_sector(self, deal_service: DealService):
        """SaaS 섹터 분류"""
        text = "B2B SaaS 클라우드 플랫폼"
        sector, keywords = deal_service.classify_sector(text)
        assert sector == DealSector.SAAS

    def test_classify_fintech_sector(self, deal_service: DealService):
        """핀테크 섹터 분류"""
        text = "간편결제 페이 핀테크 서비스"
        sector, keywords = deal_service.classify_sector(text)
        assert sector == DealSector.FINTECH

    def test_classify_other_sector(self, deal_service: DealService):
        """기타 섹터 분류"""
        text = "특별한 키워드 없음"
        sector, keywords = deal_service.classify_sector(text)
        assert sector == DealSector.OTHER
        assert len(keywords) == 0

    def test_classify_with_keywords(self, deal_service: DealService):
        """추가 키워드로 분류"""
        text = "스타트업 투자"
        keywords = ["머신러닝", "딥러닝"]
        sector, matched = deal_service.classify_sector(text, keywords)
        assert sector == DealSector.AI_DEEPTECH

    def test_classify_multiple_matches(self, deal_service: DealService):
        """여러 섹터 매칭 시 최다 매칭 선택"""
        text = "AI 인공지능 딥러닝 머신러닝 바이오"
        sector, keywords = deal_service.classify_sector(text)
        assert sector == DealSector.AI_DEEPTECH  # AI 키워드가 더 많음


class TestEstimateStage:
    """투자 단계 추정 테스트"""

    def test_estimate_seed_by_text(self, deal_service: DealService):
        """텍스트 기반 시드 추정"""
        stage = deal_service.estimate_stage(None, "시드 라운드")
        assert stage == DealStage.SEED

    def test_estimate_series_a_by_text(self, deal_service: DealService):
        """텍스트 기반 시리즈A 추정"""
        stage = deal_service.estimate_stage(None, "Series A")
        assert stage == DealStage.SERIES_A

    def test_estimate_series_b_by_text(self, deal_service: DealService):
        """텍스트 기반 시리즈B 추정"""
        stage = deal_service.estimate_stage(None, "시리즈 B")
        assert stage == DealStage.SERIES_B

    def test_estimate_pre_ipo_by_text(self, deal_service: DealService):
        """텍스트 기반 Pre-IPO 추정"""
        stage = deal_service.estimate_stage(None, "Pre-IPO")
        assert stage == DealStage.PRE_IPO

    def test_estimate_bridge_by_text(self, deal_service: DealService):
        """텍스트 기반 브릿지 추정"""
        stage = deal_service.estimate_stage(None, "브릿지 라운드")
        assert stage == DealStage.BRIDGE

    def test_estimate_seed_by_amount(self, deal_service: DealService):
        """금액 기반 시드 추정 (5억)"""
        stage = deal_service.estimate_stage(Decimal("500000000"), None)
        assert stage == DealStage.SEED

    def test_estimate_series_a_by_amount(self, deal_service: DealService):
        """금액 기반 시리즈A 추정 (50억)"""
        stage = deal_service.estimate_stage(Decimal("5000000000"), None)
        assert stage == DealStage.SERIES_A

    def test_estimate_series_b_by_amount(self, deal_service: DealService):
        """금액 기반 시리즈B 추정 (150억)"""
        stage = deal_service.estimate_stage(Decimal("15000000000"), None)
        assert stage == DealStage.SERIES_B

    def test_estimate_pre_ipo_by_amount(self, deal_service: DealService):
        """금액 기반 Pre-IPO 추정 (1500억)"""
        stage = deal_service.estimate_stage(Decimal("150000000000"), None)
        assert stage == DealStage.PRE_IPO

    def test_text_priority_over_amount(self, deal_service: DealService):
        """텍스트 우선 (텍스트와 금액 불일치)"""
        # 금액은 시리즈B 범위지만 텍스트는 시드
        stage = deal_service.estimate_stage(Decimal("15000000000"), "시드")
        assert stage == DealStage.SEED


class TestFormatAmountDisplay:
    """금액 표시 포맷 테스트"""

    def test_format_billion(self, deal_service: DealService):
        """억원 단위"""
        result = deal_service.format_amount_display(Decimal("5000000000"))
        assert result == "50억원"

    def test_format_trillion(self, deal_service: DealService):
        """조원 단위"""
        result = deal_service.format_amount_display(Decimal("1500000000000"))
        assert result == "1.5조원"

    def test_format_none(self, deal_service: DealService):
        """None 처리"""
        result = deal_service.format_amount_display(None)
        assert result is None


class TestParseAmount:
    """금액 파싱 테스트"""

    def test_parse_billion_won(self, deal_service: DealService):
        """억원 파싱"""
        result = deal_service._parse_amount({"value": "100", "unit": "억원"})
        assert result == Decimal("10000000000")

    def test_parse_million_won(self, deal_service: DealService):
        """만원 파싱"""
        result = deal_service._parse_amount({"value": "5000", "unit": "만원"})
        assert result == Decimal("50000000")

    def test_parse_dollar(self, deal_service: DealService):
        """달러 파싱 (환율 적용)"""
        result = deal_service._parse_amount({"value": "100", "unit": "만달러"})
        assert result == Decimal("1300000000")  # 100만 * 1300

    def test_parse_with_comma(self, deal_service: DealService):
        """콤마 포함 파싱"""
        result = deal_service._parse_amount({"value": "1,000", "unit": "억원"})
        assert result == Decimal("100000000000")


class TestExtractDealFromNews:
    """뉴스에서 딜 추출 테스트"""

    async def test_extract_with_amount(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_news_with_investment: NewsArticle,
        sample_company: Company,
    ):
        """금액 정보가 있는 뉴스에서 추출"""
        deal = await deal_service.extract_deal_from_news(
            db=async_session,
            news_article_id=sample_news_with_investment.id,
            investor_corp_code=sample_company.corp_code,
        )

        assert deal is not None
        assert deal.amount == Decimal("10000000000")  # 100억
        assert deal.round_stage == DealStage.SERIES_A
        assert deal.sector == DealSector.AI_DEEPTECH
        assert deal.company_id == sample_company.id
        assert deal.news_article_id == sample_news_with_investment.id

    async def test_extract_no_news(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
    ):
        """존재하지 않는 뉴스"""
        deal = await deal_service.extract_deal_from_news(
            db=async_session,
            news_article_id=99999,
        )
        assert deal is None


class TestGetDealsByCompany:
    """회사별 딜 조회 테스트"""

    async def test_get_deals(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """딜 목록 조회"""
        deals, total = await deal_service.get_deals_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
            years=5,
        )

        assert total == 4
        assert len(deals) == 4

    async def test_get_deals_filter_sector(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """섹터 필터"""
        deals, total = await deal_service.get_deals_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
            sector=DealSector.AI_DEEPTECH,
            years=5,
        )

        assert total == 1
        assert deals[0].sector == DealSector.AI_DEEPTECH

    async def test_get_deals_filter_stage(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """단계 필터"""
        deals, total = await deal_service.get_deals_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
            stage=DealStage.SERIES_A,
            years=5,
        )

        assert total == 2  # AI스타트업, 핀테크회사

    async def test_get_deals_pagination(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """페이지네이션"""
        deals, total = await deal_service.get_deals_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
            years=5,
            page=1,
            size=2,
        )

        assert total == 4
        assert len(deals) == 2

    async def test_get_deals_no_company(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
    ):
        """존재하지 않는 회사"""
        deals, total = await deal_service.get_deals_by_company(
            db=async_session,
            corp_code="99999999",
            years=5,
        )

        assert total == 0
        assert len(deals) == 0


class TestAggregation:
    """집계 테스트"""

    async def test_aggregate_by_sector(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """섹터별 집계"""
        aggregations = await deal_service.aggregate_by_sector(
            db=async_session,
            corp_code=sample_company.corp_code,
        )

        assert len(aggregations) == 4  # AI, BIO, FINTECH, SAAS
        # 딜 수로 정렬되어 있어야 함
        assert all(a["deal_count"] >= 1 for a in aggregations)

    async def test_aggregate_by_stage(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """단계별 집계"""
        aggregations = await deal_service.aggregate_by_stage(
            db=async_session,
            corp_code=sample_company.corp_code,
        )

        assert len(aggregations) == 3  # SEED, SERIES_A, SERIES_B
        # 단계 순서대로 정렬되어 있어야 함

    async def test_aggregate_by_year_filter(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """연도 필터 집계"""
        aggregations = await deal_service.aggregate_by_sector(
            db=async_session,
            corp_code=sample_company.corp_code,
            year=2025,
        )

        # 2025년 딜만 집계
        total_count = sum(a["deal_count"] for a in aggregations)
        assert total_count == 2  # AI스타트업, 바이오벤처


class TestYearlyTrends:
    """연도별 트렌드 테스트"""

    async def test_get_yearly_trends(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """연도별 트렌드 조회"""
        trends = await deal_service.get_yearly_trends(
            db=async_session,
            corp_code=sample_company.corp_code,
            years=5,
        )

        assert len(trends) == 2  # 2024, 2025
        # 연도 순으로 정렬
        years = [t["year"] for t in trends]
        assert years == sorted(years)

    async def test_get_yearly_trends_all(
        self,
        async_session: AsyncSession,
        deal_service: DealService,
        sample_deals: list[Deal],
    ):
        """전체 트렌드 조회 (회사 필터 없음)"""
        trends = await deal_service.get_yearly_trends(
            db=async_session,
            corp_code=None,
            years=5,
        )

        assert len(trends) >= 1
