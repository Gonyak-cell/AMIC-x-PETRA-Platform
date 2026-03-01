"""GP ↔ 펀드 연결 기능 테스트 (KVIC 자조합, 금감원 PEF)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.gp_fund import KVICFund, PEFFund
from app.services.fss_pef_service import FSSPEFItem, FSSPEFService
from app.services.kvic_service import KVICFundOperator, KVICService

# --- fixtures ---


@pytest.fixture
async def gp_company(async_session: AsyncSession) -> Company:
    """테스트용 GP Company 1개 생성."""
    company = Company(
        corp_name="에이티유파트너스",
        is_gp=True,
        gp_strategy_tags={"strategies": ["kvic_fund"], "sources": ["kvic"]},
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def two_gp_companies(async_session: AsyncSession) -> list[Company]:
    """테스트용 GP Company 2개 생성."""
    companies = [
        Company(
            corp_name="스틱인베스트먼트",
            is_gp=True,
            gp_strategy_tags={"strategies": ["institutional_pef"], "sources": ["freesis"]},
        ),
        Company(
            corp_name="한국투자파트너스",
            is_gp=True,
            gp_strategy_tags={"strategies": ["kvic_fund"], "sources": ["kvic"]},
        ),
    ]
    for c in companies:
        async_session.add(c)
    await async_session.flush()
    return companies


# ──────────────────────────────────────────────
# 모델 테스트
# ──────────────────────────────────────────────


class TestKVICFundModel:
    async def test_create_kvic_fund(self, async_session: AsyncSession, gp_company: Company) -> None:
        """KVICFund 생성 및 Company relationship 확인."""
        fund = KVICFund(
            company_id=gp_company.id,
            fund_name="에이티유 1호 펀드",
            fund_size=Decimal("50000"),
            operator_type="벤처투자회사",
            synced_at=datetime.now(UTC),
        )
        async_session.add(fund)
        await async_session.flush()

        assert fund.id is not None
        assert fund.company_id == gp_company.id

    async def test_multiple_funds_per_gp(self, async_session: AsyncSession, gp_company: Company) -> None:
        """동일 GP에 여러 자조합 연결 가능."""
        now = datetime.now(UTC)
        funds = [
            KVICFund(
                company_id=gp_company.id,
                fund_name=f"에이티유 {i}호 펀드",
                fund_size=Decimal(str(10000 * i)),
                synced_at=now,
            )
            for i in range(1, 4)
        ]
        for f in funds:
            async_session.add(f)
        await async_session.flush()

        stmt = select(KVICFund).where(KVICFund.company_id == gp_company.id)
        result = await async_session.execute(stmt)
        assert len(result.scalars().all()) == 3


class TestPEFFundModel:
    async def test_create_pef_fund(self, async_session: AsyncSession, two_gp_companies: list[Company]) -> None:
        """PEFFund 생성 (GP1/GP2) 및 relationship 확인."""
        gp1, gp2 = two_gp_companies
        pef = PEFFund(
            pef_name="테스트 사모 1호",
            legal_basis="자본시장법",
            total_commitment=Decimal("500"),
            gp1_company_id=gp1.id,
            gp2_company_id=gp2.id,
            synced_at=datetime.now(UTC),
        )
        async_session.add(pef)
        await async_session.flush()

        assert pef.id is not None
        assert pef.gp1_company_id == gp1.id
        assert pef.gp2_company_id == gp2.id
        assert pef.gp3_company_id is None

    async def test_pef_gp1_only(self, async_session: AsyncSession, gp_company: Company) -> None:
        """GP1만 있는 PEF (GP2/GP3 없음)."""
        pef = PEFFund(
            pef_name="단독 GP PEF",
            gp1_company_id=gp_company.id,
            total_commitment=Decimal("100"),
            synced_at=datetime.now(UTC),
        )
        async_session.add(pef)
        await async_session.flush()

        assert pef.gp2_company_id is None
        assert pef.gp3_company_id is None


# ──────────────────────────────────────────────
# KVIC 서비스 테스트 (자조합 레코드 저장)
# ──────────────────────────────────────────────


class TestKVICServiceFundSync:
    async def test_sync_creates_kvic_fund_records(self, async_session: AsyncSession) -> None:
        """KVIC 동기화 시 개별 자조합 레코드가 kvic_funds에 저장된다."""
        service = KVICService()
        items = [
            KVICFundOperator(
                fund_name="모태 1호 조합",
                operator_name="테스트운용사",
                operator_type="벤처투자회사",
                fund_size=Decimal("30000"),
            ),
            KVICFundOperator(
                fund_name="모태 2호 조합",
                operator_name="테스트운용사",
                operator_type="벤처투자회사",
                fund_size=Decimal("50000"),
            ),
            KVICFundOperator(
                fund_name="모태 3호 조합",
                operator_name="테스트운용사",
                operator_type="벤처투자회사",
                fund_size=Decimal("20000"),
            ),
        ]

        result = await service.sync_kvic_gp_data(async_session, items)

        assert result.total_items == 3
        assert result.unique_operators == 1
        assert result.created == 1

        # 개별 자조합 레코드 확인
        stmt = select(KVICFund)
        db_result = await async_session.execute(stmt)
        funds = db_result.scalars().all()
        assert len(funds) == 3
        fund_names = {f.fund_name for f in funds}
        assert fund_names == {"모태 1호 조합", "모태 2호 조합", "모태 3호 조합"}

    async def test_sync_preserves_all_fund_sizes(self, async_session: AsyncSession) -> None:
        """각 자조합의 fund_size가 개별적으로 보존된다."""
        service = KVICService()
        items = [
            KVICFundOperator(
                fund_name="소형 조합",
                operator_name="운용사A",
                fund_size=Decimal("5000"),
            ),
            KVICFundOperator(
                fund_name="대형 조합",
                operator_name="운용사A",
                fund_size=Decimal("100000"),
            ),
        ]

        await service.sync_kvic_gp_data(async_session, items)

        stmt = select(KVICFund).order_by(KVICFund.fund_size)
        db_result = await async_session.execute(stmt)
        funds = db_result.scalars().all()
        assert len(funds) == 2
        assert funds[0].fund_size == Decimal("5000")
        assert funds[1].fund_size == Decimal("100000")

    async def test_resync_replaces_existing_records(self, async_session: AsyncSession) -> None:
        """재동기화 시 기존 자조합 레코드가 교체된다."""
        service = KVICService()
        items_v1 = [
            KVICFundOperator(
                fund_name="조합 v1",
                operator_name="재동기화운용사",
                fund_size=Decimal("10000"),
            ),
        ]
        await service.sync_kvic_gp_data(async_session, items_v1)

        # v2: 이름이 다른 2개 조합
        items_v2 = [
            KVICFundOperator(
                fund_name="조합 v2-A",
                operator_name="재동기화운용사",
                fund_size=Decimal("20000"),
            ),
            KVICFundOperator(
                fund_name="조합 v2-B",
                operator_name="재동기화운용사",
                fund_size=Decimal("30000"),
            ),
        ]
        await service.sync_kvic_gp_data(async_session, items_v2)

        stmt = select(KVICFund)
        db_result = await async_session.execute(stmt)
        funds = db_result.scalars().all()
        assert len(funds) == 2
        fund_names = {f.fund_name for f in funds}
        assert "조합 v1" not in fund_names
        assert fund_names == {"조합 v2-A", "조합 v2-B"}


# ──────────────────────────────────────────────
# FSS PEF 서비스 테스트
# ──────────────────────────────────────────────


class TestFSSPEFService:
    async def test_sync_creates_pef_records(self, async_session: AsyncSession) -> None:
        """FSS PEF 동기화 시 pef_funds에 레코드가 생성된다."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="한국성장 1호 PEF",
                legal_basis="자본시장법",
                registration_date="2023-05-01",
                gp1_name="신규운용사A",
                total_commitment=Decimal("500"),
            ),
        ]

        result = await service.sync_pef_data(async_session, items)

        assert result.total_items == 1
        assert result.created == 1

        stmt = select(PEFFund)
        db_result = await async_session.execute(stmt)
        pefs = db_result.scalars().all()
        assert len(pefs) == 1
        assert pefs[0].pef_name == "한국성장 1호 PEF"
        assert pefs[0].total_commitment == Decimal("500")

    async def test_sync_creates_new_gp_company(self, async_session: AsyncSession) -> None:
        """GP 매칭 실패 시 신규 Company가 생성된다."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="테스트 PEF",
                gp1_name="새로운운용사",
                gp2_name="두번째운용사",
                total_commitment=Decimal("300"),
            ),
        ]

        result = await service.sync_pef_data(async_session, items)

        assert result.new_companies == 2  # GP1, GP2 모두 신규

        stmt = select(Company).where(Company.is_gp.is_(True))
        db_result = await async_session.execute(stmt)
        companies = db_result.scalars().all()
        names = {c.corp_name for c in companies}
        assert "새로운운용사" in names
        assert "두번째운용사" in names

    async def test_sync_matches_existing_company(self, async_session: AsyncSession, gp_company: Company) -> None:
        """기존 Company와 매칭되는 경우 신규 생성하지 않는다."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="기존 GP PEF",
                gp1_name="에이티유파트너스",  # 기존 fixture
                total_commitment=Decimal("200"),
            ),
        ]

        result = await service.sync_pef_data(async_session, items)

        assert result.matched_existing == 1
        assert result.new_companies == 0
        assert result.created == 1  # PEF 자체는 생성됨

    async def test_sync_total_commitment_decimal(self, async_session: AsyncSession) -> None:
        """총약정액이 Decimal로 정확히 저장된다."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="정밀도 테스트 PEF",
                gp1_name="정밀운용사",
                total_commitment=Decimal("12345"),
            ),
        ]

        await service.sync_pef_data(async_session, items)

        stmt = select(PEFFund)
        db_result = await async_session.execute(stmt)
        pef = db_result.scalar_one()
        assert pef.total_commitment == Decimal("12345")
