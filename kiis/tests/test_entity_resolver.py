"""Entity Resolution 테스트

- 기업명 정규화
- 자모 분해 유사도
- 별칭 매칭
- 유사도 기반 후보 추출
- 별칭 CRUD
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyAlias
from app.utils.entity_resolver import (
    EntityResolver,
    calculate_similarity,
    decompose_to_jamo,
    normalize_company_name,
)

# ──────────────── 정규화 테스트 ────────────────


class TestNormalizeCompanyName:
    def test_remove_jusikhwesa(self):
        assert normalize_company_name("주식회사 한국투자파트너스") == "한국투자파트너스"

    def test_remove_jusikhwesa_suffix(self):
        assert normalize_company_name("한국투자파트너스 주식회사") == "한국투자파트너스"

    def test_remove_parenthesis_ju(self):
        assert normalize_company_name("(주)한국투자파트너스") == "한국투자파트너스"

    def test_remove_circled_ju(self):
        assert normalize_company_name("㈜한국투자파트너스") == "한국투자파트너스"

    def test_trim_whitespace(self):
        assert normalize_company_name("  한국투자파트너스  ") == "한국투자파트너스"

    def test_collapse_multiple_spaces(self):
        assert normalize_company_name("한국  투자  파트너스") == "한국 투자 파트너스"

    def test_empty_string(self):
        assert normalize_company_name("") == ""

    def test_only_suffix(self):
        assert normalize_company_name("주식회사") == ""

    def test_remove_yuhan(self):
        assert normalize_company_name("유한회사 테스트기업") == "테스트기업"

    def test_remove_tuja_johap(self):
        assert normalize_company_name("한국벤처투자조합") == "한국벤처"


# ──────────────── 자모 분해 테스트 ────────────────


class TestDecomposeJamo:
    def test_korean_decompose(self):
        result = decompose_to_jamo("한")
        assert result == "ㅎㅏㄴ"

    def test_mixed_text(self):
        result = decompose_to_jamo("A한B")
        assert result == "AㅎㅏㄴB"  # A stays, 한→ㅎㅏㄴ, B stays

    def test_no_korean(self):
        result = decompose_to_jamo("ABC123")
        assert result == "ABC123"


# ──────────────── 유사도 계산 테스트 ────────────────


class TestCalculateSimilarity:
    def test_identical_names(self):
        score = calculate_similarity("한국투자파트너스", "한국투자파트너스")
        assert score == 1.0

    def test_with_suffix(self):
        score = calculate_similarity("한국투자파트너스 주식회사", "한국투자파트너스")
        assert score == 1.0  # 정규화 후 동일

    def test_similar_names(self):
        score = calculate_similarity("한국투자파트너스", "한국투자파트너")
        assert score > 0.8

    def test_different_names(self):
        score = calculate_similarity("한국투자파트너스", "삼성전자")
        assert score < 0.5

    def test_empty_name(self):
        score = calculate_similarity("", "한국투자파트너스")
        assert score == 0.0

    def test_both_empty(self):
        score = calculate_similarity("", "")
        assert score == 0.0

    def test_short_abbreviation(self):
        # 약칭은 유사도가 낮을 수 있음 → 별칭 사전으로 커버
        score = calculate_similarity("한투파", "한국투자파트너스")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ──────────────── EntityResolver DB 테스트 ────────────────


class TestEntityResolver:
    @pytest.fixture
    async def sample_companies(self, async_session: AsyncSession) -> list[Company]:
        """테스트용 기업 데이터"""
        companies = [
            Company(
                corp_code="00100001",
                corp_name="한국투자파트너스 주식회사",
                corp_cls="E",
            ),
            Company(
                corp_code="00100002",
                corp_name="삼성벤처투자 주식회사",
                corp_cls="E",
            ),
            Company(
                corp_code="00100003",
                corp_name="스틱인베스트먼트 주식회사",
                corp_cls="E",
            ),
            Company(
                corp_code="00100004",
                corp_name="카카오벤처스 주식회사",
                corp_cls="E",
            ),
        ]
        async_session.add_all(companies)
        await async_session.flush()
        return companies

    @pytest.fixture
    async def sample_aliases(self, async_session: AsyncSession, sample_companies: list[Company]) -> list[CompanyAlias]:
        """테스트용 별칭 데이터"""
        aliases = [
            CompanyAlias(
                alias_name="한투파",
                company_id=sample_companies[0].id,
                is_manual=True,
            ),
            CompanyAlias(
                alias_name="KVIC",
                company_id=sample_companies[0].id,
                is_manual=True,
            ),
            CompanyAlias(
                alias_name="삼성벤처",
                company_id=sample_companies[1].id,
                is_manual=True,
            ),
        ]
        async_session.add_all(aliases)
        await async_session.flush()
        return aliases

    async def test_resolve_by_alias_exact(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """별칭 정확 매칭 테스트"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "한투파")
        assert result["match"] is not None
        assert result["match"]["corp_code"] == "00100001"
        assert result["match"]["similarity"] == 1.0
        assert result["match"]["matched_by"] == "alias"

    async def test_resolve_by_alias_case_insensitive(
        self, async_session: AsyncSession, sample_companies, sample_aliases
    ):
        """별칭 대소문자 무시 매칭"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "kvic")
        assert result["match"] is not None
        assert result["match"]["corp_code"] == "00100001"

    async def test_resolve_by_corp_name_exact(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """정식 기업명 정규화 매칭"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "한국투자파트너스")
        assert result["match"] is not None
        assert result["match"]["corp_code"] == "00100001"
        assert result["match"]["matched_by"] == "exact"

    async def test_resolve_with_suffix(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """법인 접미어 포함 매칭"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "주식회사 한국투자파트너스")
        assert result["match"] is not None
        assert result["match"]["corp_code"] == "00100001"

    async def test_resolve_by_similarity(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """유사도 기반 후보 추출"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "한국투자파트너", threshold=0.7)
        assert result["match"] is not None or len(result["candidates"]) > 0

    async def test_resolve_no_match(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """매칭 불가 케이스"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "완전히다른회사이름XYZ")
        assert result["match"] is None

    async def test_resolve_empty_name(self, async_session: AsyncSession, sample_companies):
        """빈 이름"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "")
        assert result["match"] is None
        assert result["candidates"] == []

    async def test_add_alias(self, async_session: AsyncSession, sample_companies):
        """별칭 등록"""
        resolver = EntityResolver()
        alias = await resolver.add_alias(
            async_session,
            alias_name="카벤",
            company_id=sample_companies[3].id,
            is_manual=True,
        )
        assert alias.id is not None
        assert alias.alias_name == "카벤"
        assert alias.company_id == sample_companies[3].id

    async def test_add_and_resolve_alias(self, async_session: AsyncSession, sample_companies):
        """별칭 등록 후 해당 별칭으로 resolve"""
        resolver = EntityResolver()
        await resolver.add_alias(
            async_session,
            alias_name="카벤",
            company_id=sample_companies[3].id,
        )
        result = await resolver.resolve(async_session, "카벤")
        assert result["match"] is not None
        assert result["match"]["corp_code"] == "00100004"

    async def test_get_aliases(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """별칭 목록 조회"""
        resolver = EntityResolver()
        aliases = await resolver.get_aliases(async_session)
        assert len(aliases) == 3

    async def test_get_aliases_filtered(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """특정 기업 별칭만 조회"""
        resolver = EntityResolver()
        aliases = await resolver.get_aliases(async_session, company_id=sample_companies[0].id)
        assert len(aliases) == 2  # 한투파, KVIC

    async def test_delete_alias(self, async_session: AsyncSession, sample_companies, sample_aliases):
        """별칭 삭제"""
        resolver = EntityResolver()
        deleted = await resolver.delete_alias(async_session, alias_id=sample_aliases[0].id)
        assert deleted is True
        # 삭제 확인
        aliases = await resolver.get_aliases(async_session, company_id=sample_companies[0].id)
        assert len(aliases) == 1

    async def test_delete_nonexistent_alias(self, async_session: AsyncSession, sample_companies):
        """존재하지 않는 별칭 삭제"""
        resolver = EntityResolver()
        deleted = await resolver.delete_alias(async_session, alias_id=99999)
        assert deleted is False

    async def test_candidates_sorted_by_similarity(self, async_session: AsyncSession, sample_companies):
        """후보가 유사도 내림차순으로 정렬"""
        resolver = EntityResolver()
        result = await resolver.resolve(async_session, "벤처투자", threshold=0.3)
        candidates = result.get("candidates", [])
        if len(candidates) >= 2:
            for i in range(len(candidates) - 1):
                assert candidates[i]["similarity"] >= candidates[i + 1]["similarity"]
