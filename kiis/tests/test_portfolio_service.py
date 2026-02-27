"""포트폴리오 생존분석 테스트"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal, DealSector, DealStage
from app.models.portfolio import PortfolioCompany, SurvivalStatus
from app.schemas.dart import DisclosureItem
from app.services.portfolio_service import PortfolioService


@pytest.fixture
def portfolio_service() -> PortfolioService:
    """포트폴리오 서비스 인스턴스"""
    return PortfolioService()


@pytest.fixture
async def investor_company(async_session: AsyncSession) -> Company:
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
async def target_company(async_session: AsyncSession) -> Company:
    """테스트용 피투자사 (DART 등록)"""
    company = Company(
        corp_code="00200002",
        corp_name="AI스타트업 주식회사",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def sample_deals(
    async_session: AsyncSession,
    investor_company: Company,
    target_company: Company,
) -> list[Deal]:
    """테스트용 딜 데이터"""
    deals = [
        Deal(
            company_id=investor_company.id,
            target_company="AI스타트업",
            target_company_id=target_company.id,
            amount=Decimal("5000000000"),
            amount_display="50억원",
            round_stage=DealStage.SERIES_A,
            sector=DealSector.AI_DEEPTECH,
            deal_date=date(2025, 6, 15),
            deal_year=2025,
            source_type="news",
        ),
        Deal(
            company_id=investor_company.id,
            target_company="바이오벤처",
            amount=Decimal("15000000000"),
            amount_display="150억원",
            round_stage=DealStage.SERIES_B,
            sector=DealSector.BIO_HEALTH,
            deal_date=date(2025, 3, 10),
            deal_year=2025,
            source_type="news",
        ),
        Deal(
            company_id=investor_company.id,
            target_company="핀테크회사",
            amount=Decimal("3000000000"),
            amount_display="30억원",
            round_stage=DealStage.SERIES_A,
            sector=DealSector.FINTECH,
            deal_date=date(2024, 11, 20),
            deal_year=2024,
            source_type="disclosure",
        ),
    ]
    async_session.add_all(deals)
    await async_session.flush()
    return deals


@pytest.fixture
async def sample_portfolio(
    async_session: AsyncSession,
    investor_company: Company,
    target_company: Company,
    sample_deals: list[Deal],
) -> list[PortfolioCompany]:
    """테스트용 포트폴리오 데이터"""
    entries = [
        PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="AI스타트업",
            target_company_id=target_company.id,
            deal_id=sample_deals[0].id,
            survival_status=SurvivalStatus.ACTIVE,
        ),
        PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="바이오벤처",
            deal_id=sample_deals[1].id,
            survival_status=SurvivalStatus.UNKNOWN,
        ),
        PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="핀테크회사",
            deal_id=sample_deals[2].id,
            survival_status=SurvivalStatus.DISSOLVED,
        ),
    ]
    async_session.add_all(entries)
    await async_session.flush()
    return entries


class TestSyncFromDeals:
    """딜 데이터에서 포트폴리오 동기화 테스트"""

    async def test_sync_creates_portfolio_entries(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        sample_deals: list[Deal],
    ):
        """딜에서 포트폴리오 엔트리를 생성한다."""
        count = await portfolio_service.sync_from_deals(
            db=async_session,
            investor_corp_code=investor_company.corp_code,
        )

        assert count == 3  # AI스타트업, 바이오벤처, 핀테크회사

    async def test_sync_skips_existing(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        sample_deals: list[Deal],
    ):
        """이미 존재하는 엔트리는 건너뛴다."""
        # 첫 번째 동기화
        first_count = await portfolio_service.sync_from_deals(
            db=async_session,
            investor_corp_code=investor_company.corp_code,
        )
        assert first_count == 3

        # 두 번째 동기화 — 중복 생성하지 않음
        second_count = await portfolio_service.sync_from_deals(
            db=async_session,
            investor_corp_code=investor_company.corp_code,
        )
        assert second_count == 0

    async def test_sync_empty_deals(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """딜이 없는 투자사는 0을 반환한다."""
        count = await portfolio_service.sync_from_deals(
            db=async_session,
            investor_corp_code=investor_company.corp_code,
        )

        assert count == 0

    async def test_sync_unknown_company(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
    ):
        """존재하지 않는 투자사는 0을 반환한다."""
        count = await portfolio_service.sync_from_deals(
            db=async_session,
            investor_corp_code="99999999",
        )

        assert count == 0


class TestCheckSurvival:
    """생존 확인 테스트"""

    async def test_audit_found_sets_active(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        target_company: Company,
        sample_deals: list[Deal],
    ):
        """감사보고서가 발견되면 active로 설정한다."""
        # 포트폴리오 엔트리 생성 (unknown 상태)
        entry = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="AI스타트업",
            target_company_id=target_company.id,
            deal_id=sample_deals[0].id,
            survival_status=SurvivalStatus.UNKNOWN,
        )
        async_session.add(entry)
        await async_session.flush()

        # DART API 모킹 — 감사보고서 발견
        audit_disclosure = DisclosureItem(
            corp_code=target_company.corp_code,
            corp_name=target_company.corp_name,
            report_nm="감사보고서 (2024.12)",
            rcept_no="20250301000001",
            rcept_dt="20250301",
            flr_nm="AI스타트업",
        )

        with patch.object(
            portfolio_service.dart_service,
            "search_disclosures",
            new_callable=AsyncMock,
        ) as mock_search:
            # 첫 호출: 전체 공시 (해산 키워드 없음)
            # 두 번째 호출: 정기공시 (감사보고서)
            mock_search.side_effect = [
                ([audit_disclosure], 1, 1),
                ([audit_disclosure], 1, 1),
            ]

            result = await portfolio_service.check_survival(
                db=async_session,
                portfolio_id=entry.id,
            )

        assert result is not None
        assert result.survival_status == SurvivalStatus.ACTIVE
        assert result.last_audit_date == date(2025, 3, 1)
        assert result.last_audit_rcept_no == "20250301000001"
        assert result.checked_at is not None

    async def test_audit_missing(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        target_company: Company,
        sample_deals: list[Deal],
    ):
        """감사보고서가 없으면 audit_missing으로 설정한다."""
        entry = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="AI스타트업",
            target_company_id=target_company.id,
            deal_id=sample_deals[0].id,
            survival_status=SurvivalStatus.UNKNOWN,
        )
        async_session.add(entry)
        await async_session.flush()

        with patch.object(
            portfolio_service.dart_service,
            "search_disclosures",
            new_callable=AsyncMock,
        ) as mock_search:
            # 첫 호출: 전체 공시 (빈 결과)
            # 두 번째 호출: 정기공시 (빈 결과)
            mock_search.side_effect = [
                ([], 0, 0),
                ([], 0, 0),
            ]

            result = await portfolio_service.check_survival(
                db=async_session,
                portfolio_id=entry.id,
            )

        assert result is not None
        assert result.survival_status == SurvivalStatus.AUDIT_MISSING
        assert result.checked_at is not None

    async def test_dissolution_detected(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        target_company: Company,
        sample_deals: list[Deal],
    ):
        """해산 키워드가 감지되면 dissolved로 설정한다."""
        entry = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="AI스타트업",
            target_company_id=target_company.id,
            deal_id=sample_deals[0].id,
            survival_status=SurvivalStatus.ACTIVE,
        )
        async_session.add(entry)
        await async_session.flush()

        dissolution_disclosure = DisclosureItem(
            corp_code=target_company.corp_code,
            corp_name=target_company.corp_name,
            report_nm="해산사유발생보고서",
            rcept_no="20250601000001",
            rcept_dt="20250601",
            flr_nm="AI스타트업",
        )

        with patch.object(
            portfolio_service.dart_service,
            "search_disclosures",
            new_callable=AsyncMock,
        ) as mock_search:
            # 첫 호출: 전체 공시에서 해산 키워드 감지
            mock_search.return_value = ([dissolution_disclosure], 1, 1)

            result = await portfolio_service.check_survival(
                db=async_session,
                portfolio_id=entry.id,
            )

        assert result is not None
        assert result.survival_status == SurvivalStatus.DISSOLVED
        assert result.dissolution_date == date(2025, 6, 1)
        assert result.dissolution_rcept_no == "20250601000001"

    async def test_no_target_corp_code(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        sample_deals: list[Deal],
    ):
        """피투자사의 corp_code가 없으면 상태 변경 없이 반환한다."""
        entry = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="바이오벤처",
            target_company_id=None,  # corp_code 없음
            deal_id=sample_deals[1].id,
            survival_status=SurvivalStatus.UNKNOWN,
        )
        async_session.add(entry)
        await async_session.flush()

        result = await portfolio_service.check_survival(
            db=async_session,
            portfolio_id=entry.id,
        )

        assert result is not None
        assert result.survival_status == SurvivalStatus.UNKNOWN
        assert result.notes == "피투자사 DART 고유번호 미확인"
        assert result.checked_at is not None

    async def test_nonexistent_portfolio(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
    ):
        """존재하지 않는 포트폴리오 ID는 None을 반환한다."""
        result = await portfolio_service.check_survival(
            db=async_session,
            portfolio_id=99999,
        )

        assert result is None


class TestGetPortfolio:
    """포트폴리오 목록 조회 테스트"""

    async def test_paginated_list(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        sample_portfolio: list[PortfolioCompany],
    ):
        """페이지네이션이 적용된 목록을 조회한다."""
        items, total = await portfolio_service.get_portfolio_by_investor(
            db=async_session,
            corp_code=investor_company.corp_code,
            page=1,
            size=2,
        )

        assert total == 3
        assert len(items) == 2

    async def test_filter_by_status(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        sample_portfolio: list[PortfolioCompany],
    ):
        """특정 상태로 필터링한다."""
        items, total = await portfolio_service.get_portfolio_by_investor(
            db=async_session,
            corp_code=investor_company.corp_code,
            status=SurvivalStatus.ACTIVE,
        )

        assert total == 1
        assert items[0].survival_status == SurvivalStatus.ACTIVE
        assert items[0].target_company_name == "AI스타트업"

    async def test_no_company_returns_empty(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
    ):
        """존재하지 않는 투자사는 빈 결과를 반환한다."""
        items, total = await portfolio_service.get_portfolio_by_investor(
            db=async_session,
            corp_code="99999999",
        )

        assert total == 0
        assert len(items) == 0


class TestPortfolioSummary:
    """포트폴리오 요약 테스트"""

    async def test_summary_counts(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
        sample_portfolio: list[PortfolioCompany],
    ):
        """상태별 건수를 정확히 집계한다."""
        summary = await portfolio_service.get_portfolio_summary(
            db=async_session,
            corp_code=investor_company.corp_code,
        )

        assert summary["total"] == 3
        assert summary["active_count"] == 1
        assert summary["dissolved_count"] == 1
        assert summary["unknown_count"] == 1
        assert summary["audit_missing_count"] == 0
        assert summary["unicorn_count"] == 0

    async def test_summary_no_company(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
    ):
        """존재하지 않는 투자사는 모두 0인 요약을 반환한다."""
        summary = await portfolio_service.get_portfolio_summary(
            db=async_session,
            corp_code="99999999",
        )

        assert summary["total"] == 0
        assert summary["active_count"] == 0
        assert summary["audit_missing_count"] == 0
        assert summary["dissolved_count"] == 0
        assert summary["unicorn_count"] == 0
        assert summary["unknown_count"] == 0


class TestUpdateValuation:
    """기업가치 업데이트 및 유니콘 감지 테스트"""

    async def test_below_threshold(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """1조 미만 기업가치 → 유니콘 아님"""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="일반스타트업",
            survival_status=SurvivalStatus.ACTIVE,
        )
        async_session.add(portfolio)
        await async_session.flush()

        result, is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=portfolio.id,
            valuation=Decimal("500_000_000_000"),  # 5000억
        )

        assert result is not None
        assert result.is_unicorn is False
        assert result.estimated_valuation == Decimal("500_000_000_000")
        assert result.survival_status == SurvivalStatus.ACTIVE
        assert is_newly_unicorn is False

    async def test_triggers_unicorn(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """1조 이상 기업가치 → 유니콘 전환"""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="유니콘후보",
            survival_status=SurvivalStatus.ACTIVE,
        )
        async_session.add(portfolio)
        await async_session.flush()

        result, is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=portfolio.id,
            valuation=Decimal("1_500_000_000_000"),  # 1.5조
        )

        assert result is not None
        assert result.is_unicorn is True
        assert result.survival_status == SurvivalStatus.UNICORN
        assert is_newly_unicorn is True

    async def test_exact_threshold(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """정확히 1조 → 유니콘"""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="경계값회사",
            survival_status=SurvivalStatus.ACTIVE,
        )
        async_session.add(portfolio)
        await async_session.flush()

        result, is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=portfolio.id,
            valuation=Decimal("1_000_000_000_000"),  # 정확히 1조
        )

        assert result is not None
        assert result.is_unicorn is True
        assert is_newly_unicorn is True

    async def test_already_unicorn_not_newly(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """이미 유니콘인 기업 → is_newly_unicorn=False"""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="기존유니콘",
            survival_status=SurvivalStatus.UNICORN,
            is_unicorn=True,
            estimated_valuation=Decimal("2_000_000_000_000"),
        )
        async_session.add(portfolio)
        await async_session.flush()

        result, is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=portfolio.id,
            valuation=Decimal("3_000_000_000_000"),  # 3조로 업데이트
        )

        assert result is not None
        assert result.is_unicorn is True
        assert is_newly_unicorn is False

    async def test_unicorn_downgrade(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """기업가치 하락 → 유니콘 해제"""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="다운그레이드회사",
            survival_status=SurvivalStatus.UNICORN,
            is_unicorn=True,
            estimated_valuation=Decimal("1_500_000_000_000"),
        )
        async_session.add(portfolio)
        await async_session.flush()

        result, is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=portfolio.id,
            valuation=Decimal("800_000_000_000"),  # 8000억으로 하락
        )

        assert result is not None
        assert result.is_unicorn is False
        assert result.survival_status == SurvivalStatus.ACTIVE
        assert is_newly_unicorn is False

    async def test_not_found(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
    ):
        """존재하지 않는 포트폴리오 ID"""
        result, is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=99999,
            valuation=Decimal("1_000_000_000_000"),
        )

        assert result is None
        assert is_newly_unicorn is False

    async def test_dissolved_company_not_upgraded_to_unicorn(
        self,
        async_session: AsyncSession,
        portfolio_service: PortfolioService,
        investor_company: Company,
    ):
        """해산된 기업은 기업가치가 높아도 유니콘 상태로 변경되지 않음"""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="해산회사",
            survival_status=SurvivalStatus.DISSOLVED,
        )
        async_session.add(portfolio)
        await async_session.flush()

        result, _is_newly_unicorn = await portfolio_service.update_valuation(
            db=async_session,
            portfolio_id=portfolio.id,
            valuation=Decimal("2_000_000_000_000"),
        )

        assert result is not None
        assert result.is_unicorn is True  # is_unicorn 플래그는 설정
        assert result.survival_status == SurvivalStatus.DISSOLVED  # 해산 상태는 유지


class TestCheckSurvivalPreservesUnicorn:
    """생존 확인이 유니콘 상태를 보존하는지 테스트"""

    async def test_preserves_unicorn_status(
        self,
        async_session: AsyncSession,
        investor_company: Company,
        target_company: Company,
    ):
        """유니콘 기업의 생존 확인 시 UNICORN 상태가 ACTIVE로 덮어씌워지지 않는다."""
        portfolio = PortfolioCompany(
            investor_company_id=investor_company.id,
            target_company_name="유니콘기업",
            target_company_id=target_company.id,
            survival_status=SurvivalStatus.UNICORN,
            is_unicorn=True,
            estimated_valuation=Decimal("2_000_000_000_000"),
        )
        async_session.add(portfolio)
        await async_session.flush()

        # DART API 모킹: 감사보고서 있음
        mock_disclosures = [
            DisclosureItem(
                corp_code="00200002",
                corp_name="AI스타트업 주식회사",
                corp_cls="E",
                report_nm="감사보고서 (2024.12)",
                rcept_no="20250315000099",
                flr_nm="AI스타트업",
                rcept_dt="20250315",
                rm="",
            ),
        ]

        service = PortfolioService()
        service.dart_service.search_disclosures = AsyncMock(
            return_value=(mock_disclosures, 1, 1)
        )

        result = await service.check_survival(db=async_session, portfolio_id=portfolio.id)

        assert result is not None
        assert result.survival_status == SurvivalStatus.UNICORN  # ACTIVE가 아닌 UNICORN 유지
        assert result.is_unicorn is True
