"""GP 통합 조회 API (GET /gp/companies) 테스트"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.services.public_data_service import search_gp_companies

# --- fixture: GP 테스트 데이터 ---


@pytest.fixture
async def gp_companies(async_session: AsyncSession) -> list[Company]:
    """테스트용 GP Company 3개 + 비GP 1개 생성"""
    companies = [
        Company(
            corp_name="에이티유파트너스",
            is_gp=True,
            gp_aum=Decimal("500000"),
            gp_fund_count=12,
            gp_employee_count=30,
            gp_strategy_tags={"strategies": ["institutional_pef"], "sources": ["freesis"]},
        ),
        Company(
            corp_name="스틱인베스트먼트",
            is_gp=True,
            gp_aum=Decimal("1200000"),
            gp_fund_count=25,
            gp_employee_count=80,
            gp_strategy_tags={"strategies": ["institutional_pef", "kvic_fund"], "sources": ["freesis", "kvic"]},
        ),
        Company(
            corp_name="한국벤처투자운용",
            is_gp=True,
            gp_aum=None,
            gp_fund_count=5,
            gp_strategy_tags={"strategies": ["kvic_fund"], "sources": ["kvic"], "kvic_fund_count": 3},
        ),
        Company(
            corp_name="삼성전자",
            is_gp=False,
            corp_code="00126380",
        ),
    ]
    for c in companies:
        async_session.add(c)
    await async_session.flush()
    return companies


# --- search_gp_companies 서비스 함수 테스트 ---


class TestSearchGPCompanies:
    async def test_returns_only_gp(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """is_gp=True인 Company만 반환한다."""
        results, total = await search_gp_companies(async_session)
        assert total == 3
        names = {c.corp_name for c in results}
        assert "삼성전자" not in names
        assert "에이티유파트너스" in names

    async def test_filter_by_company_name(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """회사명 부분 일치 필터."""
        results, total = await search_gp_companies(async_session, company_name="파트너스")
        assert total == 1
        assert results[0].corp_name == "에이티유파트너스"

    async def test_filter_by_source_freesis(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """source=freesis 필터 — gp_strategy_tags에 freesis 포함."""
        results, total = await search_gp_companies(async_session, source="freesis")
        assert total == 2
        names = {c.corp_name for c in results}
        assert names == {"에이티유파트너스", "스틱인베스트먼트"}

    async def test_filter_by_source_kvic(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """source=kvic 필터."""
        results, total = await search_gp_companies(async_session, source="kvic")
        assert total == 2
        names = {c.corp_name for c in results}
        assert names == {"스틱인베스트먼트", "한국벤처투자운용"}

    async def test_filter_by_strategy(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """strategy=institutional_pef 필터."""
        results, total = await search_gp_companies(async_session, strategy="institutional_pef")
        assert total == 2
        names = {c.corp_name for c in results}
        assert names == {"에이티유파트너스", "스틱인베스트먼트"}

    async def test_sort_by_aum_default(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """기본 정렬: AUM 내림차순 (None은 뒤로)."""
        results, _ = await search_gp_companies(async_session)
        assert results[0].corp_name == "스틱인베스트먼트"  # AUM 1,200,000
        assert results[1].corp_name == "에이티유파트너스"  # AUM 500,000
        assert results[2].corp_name == "한국벤처투자운용"  # AUM None

    async def test_sort_by_company_name(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """sort_by=company_name — 가나다순 정렬."""
        results, _ = await search_gp_companies(async_session, sort_by="company_name")
        names = [c.corp_name for c in results]
        assert names == sorted(names)

    async def test_pagination(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """페이지네이션 — page=1, size=2 → 2건, page=2 → 1건."""
        results_p1, total = await search_gp_companies(async_session, page=1, size=2)
        assert total == 3
        assert len(results_p1) == 2

        results_p2, total = await search_gp_companies(async_session, page=2, size=2)
        assert total == 3
        assert len(results_p2) == 1

    async def test_combined_filters(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """source + strategy 동시 필터."""
        results, total = await search_gp_companies(async_session, source="kvic", strategy="institutional_pef")
        assert total == 1
        assert results[0].corp_name == "스틱인베스트먼트"

    async def test_no_results(self, async_session: AsyncSession, gp_companies: list[Company]) -> None:
        """매칭 결과 없음 — 빈 리스트 반환."""
        results, total = await search_gp_companies(async_session, company_name="존재하지않는회사")
        assert total == 0
        assert results == []
