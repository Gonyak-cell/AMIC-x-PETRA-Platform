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
from app.services.public_data_service import search_gp_companies

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


# ──────────────────────────────────────────────
# GP 총약정액 합산 테스트
# ──────────────────────────────────────────────


class TestGPTotalCommitmentAggregation:
    async def test_single_gp_single_pef(self, async_session: AsyncSession) -> None:
        """단일 GP + 단일 PEF → gp_total_commitment = 해당 PEF 약정액."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="단독 PEF",
                gp1_name="합산테스트GP",
                total_commitment=Decimal("1000"),
            ),
        ]

        await service.sync_pef_data(async_session, items)

        stmt = select(Company).where(Company.corp_name == "합산테스트GP")
        result = await async_session.execute(stmt)
        company = result.scalar_one()
        assert company.gp_total_commitment == Decimal("1000")

    async def test_single_gp_multiple_pefs(self, async_session: AsyncSession) -> None:
        """동일 GP가 여러 PEF에 GP1로 참여 → 총약정액 합산."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="PEF Alpha",
                gp1_name="다중PEF운용사",
                total_commitment=Decimal("500"),
            ),
            FSSPEFItem(
                pef_name="PEF Beta",
                gp1_name="다중PEF운용사",
                total_commitment=Decimal("300"),
            ),
            FSSPEFItem(
                pef_name="PEF Gamma",
                gp1_name="다중PEF운용사",
                total_commitment=Decimal("200"),
            ),
        ]

        await service.sync_pef_data(async_session, items)

        stmt = select(Company).where(Company.corp_name == "다중PEF운용사")
        result = await async_session.execute(stmt)
        company = result.scalar_one()
        assert company.gp_total_commitment == Decimal("1000")

    async def test_coop_pef_double_counted(self, async_session: AsyncSession) -> None:
        """공동 운용 PEF는 각 GP에 중복 합산된다."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="공동운용 PEF",
                gp1_name="주GP운용사",
                gp2_name="공동GP운용사",
                total_commitment=Decimal("800"),
            ),
        ]

        await service.sync_pef_data(async_session, items)

        stmt = select(Company).where(Company.corp_name == "주GP운용사")
        result = await async_session.execute(stmt)
        gp1 = result.scalar_one()
        assert gp1.gp_total_commitment == Decimal("800")

        stmt2 = select(Company).where(Company.corp_name == "공동GP운용사")
        result2 = await async_session.execute(stmt2)
        gp2 = result2.scalar_one()
        assert gp2.gp_total_commitment == Decimal("800")

    async def test_mixed_roles_aggregation(self, async_session: AsyncSession) -> None:
        """GP1로 단독 참여 + GP2로 공동 참여 → 합산."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="단독 PEF",
                gp1_name="복합역할GP",
                total_commitment=Decimal("600"),
            ),
            FSSPEFItem(
                pef_name="공동 PEF",
                gp1_name="다른운용사",
                gp2_name="복합역할GP",
                total_commitment=Decimal("400"),
            ),
        ]

        await service.sync_pef_data(async_session, items)

        stmt = select(Company).where(Company.corp_name == "복합역할GP")
        result = await async_session.execute(stmt)
        company = result.scalar_one()
        # GP1: 600, GP2: 400 → 합계 1000
        assert company.gp_total_commitment == Decimal("1000")

    async def test_zero_commitment_excluded(self, async_session: AsyncSession) -> None:
        """총약정액이 0 또는 None인 PEF는 합산에서 제외된다."""
        service = FSSPEFService()
        items = [
            FSSPEFItem(
                pef_name="약정액 있는 PEF",
                gp1_name="제로테스트GP",
                total_commitment=Decimal("500"),
            ),
            FSSPEFItem(
                pef_name="약정액 없는 PEF",
                gp1_name="제로테스트GP",
                total_commitment=None,
            ),
        ]

        await service.sync_pef_data(async_session, items)

        stmt = select(Company).where(Company.corp_name == "제로테스트GP")
        result = await async_session.execute(stmt)
        company = result.scalar_one()
        assert company.gp_total_commitment == Decimal("500")


# ──────────────────────────────────────────────
# Detail API — GP1+GP2+GP3 PEF 병합 중복 제거 테스트
# ──────────────────────────────────────────────


class TestDetailAPIPEFMerge:
    """GP 상세 조회 시 GP1/GP2/GP3 역할 PEF 병합 및 중복 제거 검증."""

    async def test_gp2_pef_included_in_detail(self, async_session: AsyncSession) -> None:
        """GP2로만 참여하는 PEF도 상세 조회에 포함된다."""
        now = datetime.now(UTC)
        gp_a = Company(corp_name="DetailGP_A", is_gp=True)
        gp_b = Company(corp_name="DetailGP_B", is_gp=True)
        async_session.add_all([gp_a, gp_b])
        await async_session.flush()

        # GP_A가 GP1, GP_B가 GP2인 PEF
        pef = PEFFund(
            pef_name="공동운용 상세테스트",
            gp1_company_id=gp_a.id,
            gp2_company_id=gp_b.id,
            total_commitment=Decimal("500"),
            synced_at=now,
        )
        async_session.add(pef)
        await async_session.flush()

        # GP_B 관점에서 조회 — GP2로 참여한 PEF가 보여야 함
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Company)
            .where(Company.id == gp_b.id)
            .options(
                selectinload(Company.pef_funds_as_gp1),
                selectinload(Company.pef_funds_as_gp2).selectinload(PEFFund.gp1_company),
                selectinload(Company.pef_funds_as_gp3),
            )
        )
        result = await async_session.execute(stmt)
        company = result.scalar_one()

        # GP1 PEF는 없고, GP2 PEF가 1건
        assert len(company.pef_funds_as_gp1) == 0
        assert len(company.pef_funds_as_gp2) == 1
        assert company.pef_funds_as_gp2[0].pef_name == "공동운용 상세테스트"

    async def test_pef_deduplication_gp1_and_gp2(self, async_session: AsyncSession) -> None:
        """동일 GP가 GP1+GP2로 동시 참여할 수 없지만, 병합 시 중복 제거가 동작한다."""
        now = datetime.now(UTC)
        gp_a = Company(corp_name="DedupeGP_A", is_gp=True)
        gp_b = Company(corp_name="DedupeGP_B", is_gp=True)
        async_session.add_all([gp_a, gp_b])
        await async_session.flush()

        # GP_A가 GP1인 PEF 1건, GP_A가 GP2인 PEF 1건 (별도 PEF)
        pef1 = PEFFund(
            pef_name="GP_A 주도 PEF",
            gp1_company_id=gp_a.id,
            total_commitment=Decimal("300"),
            synced_at=now,
        )
        pef2 = PEFFund(
            pef_name="GP_B 주도 PEF",
            gp1_company_id=gp_b.id,
            gp2_company_id=gp_a.id,
            total_commitment=Decimal("200"),
            synced_at=now,
        )
        async_session.add_all([pef1, pef2])
        await async_session.flush()

        # GP_A: GP1 PEF 1건 + GP2 PEF 1건 = 총 2건 (중복 없음)
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Company)
            .where(Company.id == gp_a.id)
            .options(
                selectinload(Company.pef_funds_as_gp1),
                selectinload(Company.pef_funds_as_gp2),
                selectinload(Company.pef_funds_as_gp3),
            )
        )
        result = await async_session.execute(stmt)
        company = result.scalar_one()

        # seen_pef_ids 중복 제거 로직 시뮬레이션
        seen_pef_ids: set[int] = set()
        merged: list[PEFFund] = []
        for p in company.pef_funds_as_gp1:
            seen_pef_ids.add(p.id)
            merged.append(p)
        for p in company.pef_funds_as_gp2:
            if p.id not in seen_pef_ids:
                seen_pef_ids.add(p.id)
                merged.append(p)
        for p in company.pef_funds_as_gp3:
            if p.id not in seen_pef_ids:
                merged.append(p)

        assert len(merged) == 2
        pef_names = {p.pef_name for p in merged}
        assert pef_names == {"GP_A 주도 PEF", "GP_B 주도 PEF"}


# ──────────────────────────────────────────────
# sort_by="commitment" 정렬 테스트
# ──────────────────────────────────────────────


class TestSortByCommitment:
    """search_gp_companies의 sort_by="commitment" 정렬 검증."""

    async def test_sort_by_commitment_descending(self, async_session: AsyncSession) -> None:
        """gp_total_commitment 기준 내림차순 정렬."""
        companies = [
            Company(corp_name="Low_GP", is_gp=True, gp_total_commitment=Decimal("100")),
            Company(corp_name="High_GP", is_gp=True, gp_total_commitment=Decimal("9000")),
            Company(corp_name="Mid_GP", is_gp=True, gp_total_commitment=Decimal("500")),
        ]
        for c in companies:
            async_session.add(c)
        await async_session.flush()
        await async_session.commit()

        results, total = await search_gp_companies(
            async_session,
            sort_by="commitment",
            page=1,
            size=10,
        )

        assert total == 3
        names = [c.corp_name for c in results]
        assert names == ["High_GP", "Mid_GP", "Low_GP"]

    async def test_sort_by_commitment_nulls_last(self, async_session: AsyncSession) -> None:
        """gp_total_commitment가 None인 GP는 뒤로 정렬."""
        companies = [
            Company(corp_name="No_Commitment_GP", is_gp=True, gp_total_commitment=None),
            Company(corp_name="Has_Commitment_GP", is_gp=True, gp_total_commitment=Decimal("200")),
        ]
        for c in companies:
            async_session.add(c)
        await async_session.flush()
        await async_session.commit()

        results, total = await search_gp_companies(
            async_session,
            sort_by="commitment",
            page=1,
            size=10,
        )

        assert total == 2
        assert results[0].corp_name == "Has_Commitment_GP"
        assert results[1].corp_name == "No_Commitment_GP"
