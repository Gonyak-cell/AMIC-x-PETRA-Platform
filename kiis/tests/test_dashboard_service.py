"""대시보드 서비스 테스트"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal, DealSector
from app.models.disclosure import Disclosure
from app.models.news import NewsArticle
from app.models.reputation import ReputationScore
from app.services.dashboard_service import DashboardService


@pytest.fixture
def dashboard_service() -> DashboardService:
    """대시보드 서비스 인스턴스"""
    return DashboardService()


class TestGetSummary:
    """빈 DB에서 대시보드 요약 테스트"""

    async def test_empty_db_returns_zero_counts(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """빈 DB에서도 정상 동작하며 모든 count가 0이다."""
        summary = await dashboard_service.get_summary(async_session)

        assert len(summary["counts"]) == 5
        for item in summary["counts"]:
            assert item["count"] == 0

        assert summary["recent_news_count"] == 0
        assert summary["recent_deals"] == []
        assert summary["risk_companies"] == []
        assert len(summary["data_freshness"]) == 3

    async def test_summary_count_labels(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """counts 항목의 label이 올바르다."""
        summary = await dashboard_service.get_summary(async_session)

        labels = [item["label"] for item in summary["counts"]]
        assert labels == ["기업", "펀드", "리츠", "뉴스", "딜"]


class TestCountRecent:
    """최근 뉴스 카운트 테스트"""

    async def test_count_recent_news_within_7_days(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """7일 이내 뉴스만 카운트한다."""
        now = datetime.now(UTC)

        # 7일 이내 뉴스 2건
        for i in range(2):
            article = NewsArticle(
                title=f"최근 뉴스 {i}",
                source="platum",
                url=f"https://example.com/recent/{i}",
                url_hash=NewsArticle.generate_url_hash(f"https://example.com/recent/{i}"),
                published_at=now - timedelta(days=3),
            )
            async_session.add(article)

        # 8일 전 뉴스 1건 (카운트 제외)
        old_article = NewsArticle(
            title="오래된 뉴스",
            source="dealsite",
            url="https://example.com/old/1",
            url_hash=NewsArticle.generate_url_hash("https://example.com/old/1"),
            published_at=now - timedelta(days=8),
        )
        async_session.add(old_article)
        await async_session.flush()

        count = await dashboard_service._count_recent_news(async_session)
        assert count == 2


class TestRecentDeals:
    """최근 딜 반환 테스트"""

    async def test_empty_db_returns_empty_list(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """빈 DB에서 빈 리스트를 반환한다."""
        deals = await dashboard_service._get_recent_deals(async_session)
        assert deals == []

    async def test_returns_recent_deals_ordered(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """최근 딜을 날짜 역순으로 반환한다."""
        company = Company(corp_code="00100001", corp_name="테스트투자", corp_cls="E")
        async_session.add(company)
        await async_session.flush()

        deals_data = [
            Deal(
                company_id=company.id,
                target_company="회사A",
                amount_display="50억원",
                sector=DealSector.AI_DEEPTECH,
                deal_date=date(2025, 1, 10),
                deal_year=2025,
            ),
            Deal(
                company_id=company.id,
                target_company="회사B",
                amount_display="100억원",
                sector=DealSector.BIO_HEALTH,
                deal_date=date(2025, 6, 15),
                deal_year=2025,
            ),
        ]
        async_session.add_all(deals_data)
        await async_session.flush()

        result = await dashboard_service._get_recent_deals(async_session, limit=5)

        assert len(result) == 2
        # 최신 딜이 먼저
        assert result[0]["target_company"] == "회사B"
        assert result[1]["target_company"] == "회사A"

    async def test_respects_limit(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """limit 파라미터를 준수한다."""
        company = Company(corp_code="00200001", corp_name="제한테스트", corp_cls="E")
        async_session.add(company)
        await async_session.flush()

        for i in range(10):
            deal = Deal(
                company_id=company.id,
                target_company=f"회사{i}",
                deal_date=date(2025, 1, i + 1),
                deal_year=2025,
            )
            async_session.add(deal)
        await async_session.flush()

        result = await dashboard_service._get_recent_deals(async_session, limit=3)
        assert len(result) == 3


class TestRiskCompanies:
    """Risk 기업 조회 테스트"""

    async def test_empty_db_returns_empty_list(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """빈 DB에서 빈 리스트를 반환한다."""
        result = await dashboard_service._get_risk_companies(async_session)
        assert result == []

    async def test_returns_only_risk_companies(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """status_tag가 'risk'인 기업만 반환한다."""
        now = datetime.now(UTC)

        company_risk = Company(corp_code="R0000001", corp_name="리스크기업", corp_cls="E")
        company_stable = Company(corp_code="S0000001", corp_name="안정기업", corp_cls="E")
        async_session.add_all([company_risk, company_stable])
        await async_session.flush()

        score_risk = ReputationScore(
            company_id=company_risk.id,
            total_score=Decimal("0.2500"),
            status_tag="risk",
            scored_at=now,
        )
        score_stable = ReputationScore(
            company_id=company_stable.id,
            total_score=Decimal("0.7000"),
            status_tag="stable",
            scored_at=now,
        )
        async_session.add_all([score_risk, score_stable])
        await async_session.flush()

        result = await dashboard_service._get_risk_companies(async_session)

        assert len(result) == 1
        assert result[0]["corp_code"] == "R0000001"
        assert result[0]["corp_name"] == "리스크기업"
        assert result[0]["status_tag"] == "risk"
        assert result[0]["total_score"] == 0.25


class TestDataFreshness:
    """데이터 신선도 테스트"""

    async def test_empty_db_freshness(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """빈 DB에서 count 0, latest_at None을 반환한다."""
        freshness = await dashboard_service._get_data_freshness(async_session)

        assert len(freshness) == 3

        entities = {f["entity"] for f in freshness}
        assert entities == {"뉴스", "딜", "공시"}

        for item in freshness:
            assert item["count"] == 0
            assert item["latest_at"] is None

    async def test_freshness_with_data(
        self,
        async_session: AsyncSession,
        dashboard_service: DashboardService,
    ):
        """데이터가 있으면 count와 latest_at이 설정된다."""
        article = NewsArticle(
            title="테스트 뉴스",
            source="platum",
            url="https://example.com/fresh/1",
            url_hash=NewsArticle.generate_url_hash("https://example.com/fresh/1"),
            published_at=datetime.now(UTC),
        )
        async_session.add(article)

        disclosure = Disclosure(
            corp_code="00100001",
            report_nm="사업보고서",
            rcept_no="20250101000001",
            dart_viewer_url="https://dart.fss.or.kr/viewer/1",
        )
        async_session.add(disclosure)
        await async_session.flush()

        freshness = await dashboard_service._get_data_freshness(async_session)

        freshness_map = {f["entity"]: f for f in freshness}

        assert freshness_map["뉴스"]["count"] == 1
        assert freshness_map["뉴스"]["latest_at"] is not None

        assert freshness_map["공시"]["count"] == 1
        assert freshness_map["공시"]["latest_at"] is not None

        assert freshness_map["딜"]["count"] == 0
        assert freshness_map["딜"]["latest_at"] is None
