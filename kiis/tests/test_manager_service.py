"""심사역 추적 서비스 테스트"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal, DealSector, DealStage
from app.models.fund import Fund, FundManager
from app.models.manager import ManagerMovement, MovementType
from app.services.manager_service import ManagerService


@pytest.fixture
def manager_service() -> ManagerService:
    """심사역 서비스 인스턴스"""
    return ManagerService()


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
async def sample_company_b(async_session: AsyncSession) -> Company:
    """테스트용 투자사 B"""
    company = Company(
        corp_code="00100002",
        corp_name="스톤브릿지벤처스 주식회사",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def sample_fund(async_session: AsyncSession, sample_company: Company) -> Fund:
    """테스트용 펀드"""
    fund = Fund(
        fund_code="FUND001",
        fund_name="한투 AI 1호",
        company_id=sample_company.id,
        fund_type="blind",
        company_name=sample_company.corp_name,
        is_active=True,
    )
    async_session.add(fund)
    await async_session.flush()
    return fund


@pytest.fixture
async def sample_fund_b(async_session: AsyncSession, sample_company_b: Company) -> Fund:
    """테스트용 펀드 B"""
    fund = Fund(
        fund_code="FUND002",
        fund_name="스톤브릿지 2호",
        company_id=sample_company_b.id,
        fund_type="blind",
        company_name=sample_company_b.corp_name,
        is_active=True,
    )
    async_session.add(fund)
    await async_session.flush()
    return fund


@pytest.fixture
async def resigned_manager(async_session: AsyncSession, sample_fund: Fund) -> FundManager:
    """사임한 심사역"""
    manager = FundManager(
        fund_id=sample_fund.id,
        manager_name="김철수",
        position="이사",
        role="심사역",
        career_years=10,
        appointed_date=date(2020, 3, 1),
        resigned_date=date(2025, 6, 30),
        is_active=False,
        specialty_sectors='["ai_deeptech", "fintech"]',
        total_deals_involved=5,
    )
    async_session.add(manager)
    await async_session.flush()
    return manager


@pytest.fixture
async def active_manager(async_session: AsyncSession, sample_fund: Fund) -> FundManager:
    """재직 중인 심사역"""
    manager = FundManager(
        fund_id=sample_fund.id,
        manager_name="이영희",
        position="부장",
        role="펀드매니저",
        career_years=8,
        appointed_date=date(2022, 1, 15),
        is_active=True,
        specialty_sectors='["bio_health", "saas"]',
        total_deals_involved=3,
    )
    async_session.add(manager)
    await async_session.flush()
    return manager


@pytest.fixture
async def sample_deals(async_session: AsyncSession, sample_company: Company) -> list[Deal]:
    """테스트용 딜 데이터"""
    deals = [
        Deal(
            company_id=sample_company.id,
            target_company="AI스타트업",
            amount=Decimal("5000000000"),
            amount_display="50억원",
            round_stage=DealStage.SERIES_A,
            sector=DealSector.AI_DEEPTECH,
            deal_date=date(2025, 6, 15),
            deal_year=2025,
            source_type="news",
        ),
        Deal(
            company_id=sample_company.id,
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
async def sample_movements(
    async_session: AsyncSession,
    sample_company: Company,
    sample_company_b: Company,
    sample_fund: Fund,
    sample_fund_b: Fund,
) -> list[ManagerMovement]:
    """테스트용 이동 이력"""
    movements = [
        ManagerMovement(
            manager_name="박지훈",
            from_company_id=sample_company.id,
            from_company_name=sample_company.corp_name,
            from_fund_id=sample_fund.id,
            to_company_id=sample_company_b.id,
            to_company_name=sample_company_b.corp_name,
            to_fund_id=sample_fund_b.id,
            movement_type=MovementType.TRANSFER,
            detected_at=datetime(2025, 7, 1, tzinfo=UTC),
            source="kofia",
            notes="이직",
        ),
        ManagerMovement(
            manager_name="최민수",
            from_company_id=sample_company.id,
            from_company_name=sample_company.corp_name,
            from_fund_id=sample_fund.id,
            to_company_id=None,
            to_company_name=None,
            to_fund_id=None,
            movement_type=MovementType.RESIGNATION,
            detected_at=datetime(2025, 5, 15, tzinfo=UTC),
            source="kofia",
            notes="사임",
        ),
        ManagerMovement(
            manager_name="정수진",
            from_company_id=None,
            from_company_name=None,
            from_fund_id=None,
            to_company_id=sample_company_b.id,
            to_company_name=sample_company_b.corp_name,
            to_fund_id=sample_fund_b.id,
            movement_type=MovementType.APPOINTMENT,
            detected_at=datetime(2025, 4, 1, tzinfo=UTC),
            source="kofia",
            notes="신규 임명",
        ),
    ]
    async_session.add_all(movements)
    await async_session.flush()
    return movements


class TestDetectMovements:
    """이동 감지 테스트"""

    async def test_detects_resignation(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        resigned_manager: FundManager,
        sample_fund: Fund,
    ):
        """사임한 심사역의 이동 이벤트를 감지한다."""
        movements = await manager_service.detect_movements(db=async_session)

        # 사임 이벤트가 감지되어야 함
        resignation_movements = [m for m in movements if m.movement_type == MovementType.RESIGNATION]
        assert len(resignation_movements) >= 1

        resignation = resignation_movements[0]
        assert resignation.manager_name == "김철수"
        assert resignation.from_fund_id == sample_fund.id
        assert resignation.to_company_id is None
        assert resignation.source == "kofia"

    async def test_detects_new_appointment(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        active_manager: FundManager,
        sample_fund: Fund,
    ):
        """신규 임명된 심사역의 이동 이벤트를 감지한다."""
        movements = await manager_service.detect_movements(db=async_session)

        # 신규 임명 이벤트가 감지되어야 함
        appointment_movements = [m for m in movements if m.movement_type == MovementType.APPOINTMENT]
        assert len(appointment_movements) >= 1

        appointment = appointment_movements[0]
        assert appointment.manager_name == "이영희"
        assert appointment.to_fund_id == sample_fund.id
        assert appointment.from_company_id is None
        assert appointment.source == "kofia"

    async def test_no_changes(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
    ):
        """변경 사항이 없으면 빈 목록을 반환한다."""
        movements = await manager_service.detect_movements(db=async_session)
        assert len(movements) == 0

    async def test_no_duplicate_detection(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        resigned_manager: FundManager,
    ):
        """동일 이동을 중복 감지하지 않는다."""
        # 첫 번째 스캔
        first_movements = await manager_service.detect_movements(db=async_session)
        assert len(first_movements) >= 1

        # 두 번째 스캔 - 이미 기록된 이동은 감지하지 않아야 함
        second_movements = await manager_service.detect_movements(db=async_session)
        # 사임은 이미 기록되었으므로 다시 감지되지 않아야 함
        resignation_movements = [m for m in second_movements if m.movement_type == MovementType.RESIGNATION]
        assert len(resignation_movements) == 0


class TestManagerProfile:
    """심사역 프로필 테스트"""

    async def test_profile_with_deals(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        active_manager: FundManager,
        sample_fund: Fund,
        sample_company: Company,
        sample_deals: list[Deal],
    ):
        """심사역 프로필에 딜 정보가 포함된다."""
        profile = await manager_service.get_manager_profile(
            db=async_session,
            manager_name="이영희",
        )

        assert profile["manager_name"] == "이영희"
        assert profile["current_company"] == sample_company.corp_name
        assert profile["current_fund"] == sample_fund.fund_name
        assert profile["career_years"] == 8
        assert profile["total_deals_involved"] == 3
        assert "bio_health" in profile["specialty_sectors"]
        assert len(profile["deals"]) == 2  # sample_deals에 2개

    async def test_profile_not_found(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
    ):
        """존재하지 않는 심사역은 빈 프로필을 반환한다."""
        profile = await manager_service.get_manager_profile(
            db=async_session,
            manager_name="존재하지않는사람",
        )

        assert profile["manager_name"] == "존재하지않는사람"
        assert profile["current_company"] is None
        assert profile["current_fund"] is None
        assert profile["career_years"] is None
        assert profile["total_deals_involved"] == 0
        assert len(profile["movements"]) == 0
        assert len(profile["deals"]) == 0

    async def test_profile_with_movements(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        active_manager: FundManager,
        sample_fund: Fund,
        sample_company: Company,
    ):
        """심사역 프로필에 이동 이력이 포함된다."""
        # 먼저 이동 감지 실행하여 appointment 기록 생성
        await manager_service.detect_movements(db=async_session)

        profile = await manager_service.get_manager_profile(
            db=async_session,
            manager_name="이영희",
        )

        assert len(profile["movements"]) >= 1
        assert profile["movements"][0].manager_name == "이영희"


class TestMovements:
    """이동 이력 조회 테스트"""

    async def test_paginated_movements(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        sample_movements: list[ManagerMovement],
    ):
        """페이지네이션이 정상 동작한다."""
        # 전체 조회
        movements, total = await manager_service.get_movements(
            db=async_session,
            page=1,
            size=2,
        )

        assert total == 3
        assert len(movements) == 2

        # 두 번째 페이지
        movements_p2, total_p2 = await manager_service.get_movements(
            db=async_session,
            page=2,
            size=2,
        )

        assert total_p2 == 3
        assert len(movements_p2) == 1

    async def test_filter_by_manager_name(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        sample_movements: list[ManagerMovement],
    ):
        """심사역 이름으로 필터링한다."""
        movements, total = await manager_service.get_movements(
            db=async_session,
            manager_name="박지훈",
        )

        assert total == 1
        assert len(movements) == 1
        assert movements[0].manager_name == "박지훈"
        assert movements[0].movement_type == MovementType.TRANSFER

    async def test_movements_by_company(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        sample_company: Company,
        sample_movements: list[ManagerMovement],
    ):
        """기업별 이동 이력을 조회한다."""
        movements, total = await manager_service.get_movements_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
        )

        # sample_company는 from_company로 2건 (박지훈 이직, 최민수 사임)
        assert total == 2
        assert len(movements) == 2

    async def test_movements_by_company_not_found(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
    ):
        """존재하지 않는 기업은 빈 결과를 반환한다."""
        movements, total = await manager_service.get_movements_by_company(
            db=async_session,
            corp_code="99999999",
        )

        assert total == 0
        assert len(movements) == 0

    async def test_movements_by_company_b(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
        sample_company_b: Company,
        sample_movements: list[ManagerMovement],
    ):
        """기업 B 관련 이동 이력을 조회한다."""
        movements, total = await manager_service.get_movements_by_company(
            db=async_session,
            corp_code=sample_company_b.corp_code,
        )

        # sample_company_b는 to_company로 2건 (박지훈 이직, 정수진 임명)
        assert total == 2
        assert len(movements) == 2

    async def test_empty_movements(
        self,
        async_session: AsyncSession,
        manager_service: ManagerService,
    ):
        """이동 이력이 없으면 빈 결과를 반환한다."""
        movements, total = await manager_service.get_movements(
            db=async_session,
        )

        assert total == 0
        assert len(movements) == 0
