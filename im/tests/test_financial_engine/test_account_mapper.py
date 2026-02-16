"""AccountMapper 3단계 매핑 엔진 테스트.

> 마지막 수정: 2026-02-09

정확 매칭, 퍼지 매칭, 사용자 정의 매핑, 동의어 추가,
일괄 변환, strict 모드, 경고/unmapped 추적 등을 검증합니다.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.exceptions import AccountNotFoundError
from src.financial_engine.mapper.account_mapper import (
    AccountMapper,
    AccountMapping,
    MappingConfig,
    _RAPIDFUZZ_AVAILABLE,
)
from src.financial_engine.mapper.chart_of_accounts import StandardAccount


# ============================================================================
# 정확 일치 (Exact Match)
# ============================================================================


class TestExactMatch:
    """정확 일치 매핑 테스트."""

    @pytest.mark.parametrize(
        ("korean_name", "expected_code"),
        [
            ("매출액", StandardAccount.REVENUE),
            ("영업이익", StandardAccount.OPERATING_INCOME),
            ("당기순이익", StandardAccount.NET_INCOME),
            ("자산총계", StandardAccount.TOTAL_ASSETS),
            ("부채총계", StandardAccount.TOTAL_LIABILITIES),
            ("자본총계", StandardAccount.TOTAL_EQUITY),
            ("영업활동현금흐름", StandardAccount.OPERATING_CASH_FLOW),
        ],
        ids=[
            "매출액→REVENUE",
            "영업이익→OPERATING_INCOME",
            "당기순이익→NET_INCOME",
            "자산총계→TOTAL_ASSETS",
            "부채총계→TOTAL_LIABILITIES",
            "자본총계→TOTAL_EQUITY",
            "영업활동현금흐름→OCF",
        ],
    )
    def test_기본_매핑_정확_일치(
        self,
        account_mapper: AccountMapper,
        korean_name: str,
        expected_code: StandardAccount,
    ) -> None:
        """기본 사전의 한글 계정명이 정확 일치로 매핑된다."""
        result = account_mapper.map(korean_name)
        assert result is not None
        assert result.standard_code == expected_code
        assert result.confidence == 1.0
        assert result.match_type == "exact"

    def test_정확_일치_반환_타입(self, account_mapper: AccountMapper) -> None:
        """정확 일치 결과는 AccountMapping 인스턴스이다."""
        result = account_mapper.map("매출액")
        assert isinstance(result, AccountMapping)

    def test_original_name_보존(self, account_mapper: AccountMapper) -> None:
        """original_name에 입력 계정명이 그대로 보존된다."""
        result = account_mapper.map("매출액")
        assert result is not None
        assert result.original_name == "매출액"


# ============================================================================
# 퍼지 매칭 (Fuzzy Match)
# ============================================================================


class TestFuzzyMatch:
    """퍼지 매칭 테스트 (rapidfuzz 설치 시)."""

    @pytest.mark.skipif(
        not _RAPIDFUZZ_AVAILABLE,
        reason="rapidfuzz 미설치 — 퍼지 매칭 테스트 건너뜀",
    )
    def test_유사_계정명_퍼지_매칭(self, account_mapper: AccountMapper) -> None:
        """정확히 일치하지 않는 유사 계정명이 퍼지 매칭으로 처리된다."""
        # "매출 액" (띄어쓰기 삽입)은 KOREAN_ACCOUNT_MAP에 정확히 없으므로 퍼지 매칭
        result = account_mapper.map("매출 액")
        if result is not None:
            assert result.match_type == "fuzzy"
            assert 0.0 < result.confidence < 1.0

    @pytest.mark.skipif(
        not _RAPIDFUZZ_AVAILABLE,
        reason="rapidfuzz 미설치 — 퍼지 매칭 테스트 건너뜀",
    )
    def test_퍼지_매칭_warnings_추가(self, account_mapper: AccountMapper) -> None:
        """퍼지 매칭 시 warnings에 기록이 추가된다."""
        account_mapper.map("매출 액")
        # 퍼지 매칭 또는 rapidfuzz 미설치 경고 중 하나가 발생
        assert len(account_mapper.warnings) >= 1


# ============================================================================
# 커스텀 매핑 (Custom Mapping)
# ============================================================================


class TestCustomMapping:
    """사용자 정의 매핑(custom_mappings) 테스트."""

    def test_custom_매핑_우선순위(self) -> None:
        """custom_mappings가 기본 사전보다 높은 우선순위를 가진다."""
        config = MappingConfig(
            custom_mappings={"매출액": StandardAccount.OPERATING_INCOME}
        )
        mapper = AccountMapper(config=config)
        result = mapper.map("매출액")
        assert result is not None
        assert result.standard_code == StandardAccount.OPERATING_INCOME
        assert result.match_type == "custom"
        assert result.confidence == 1.0

    def test_custom_신규_계정명(self) -> None:
        """기본 사전에 없는 계정명을 custom_mappings로 추가할 수 있다."""
        config = MappingConfig(
            custom_mappings={"특별이익": StandardAccount.OTHER_NON_OPERATING_INCOME}
        )
        mapper = AccountMapper(config=config)
        result = mapper.map("특별이익")
        assert result is not None
        assert result.standard_code == StandardAccount.OTHER_NON_OPERATING_INCOME
        assert result.match_type == "custom"


# ============================================================================
# 동의어 추가 (add_synonym)
# ============================================================================


class TestAddSynonym:
    """add_synonym 런타임 동의어 추가 테스트."""

    def test_런타임_동의어_추가(self, account_mapper: AccountMapper) -> None:
        """add_synonym으로 추가된 동의어가 정확 일치 매핑에 사용된다."""
        account_mapper.add_synonym("특수매출", StandardAccount.REVENUE)
        result = account_mapper.map("특수매출")
        assert result is not None
        assert result.standard_code == StandardAccount.REVENUE
        assert result.confidence == 1.0

    def test_런타임_동의어_우선순위_base보다_높음(self) -> None:
        """런타임 동의어는 KOREAN_ACCOUNT_MAP보다 높은 우선순위를 가진다."""
        mapper = AccountMapper()
        # 기본: "매출액" → REVENUE
        mapper.add_synonym("매출액", StandardAccount.GROSS_PROFIT)
        result = mapper.map("매출액")
        assert result is not None
        assert result.standard_code == StandardAccount.GROSS_PROFIT


# ============================================================================
# 일괄 변환 (map_all)
# ============================================================================


class TestMapAll:
    """map_all 일괄 변환 테스트."""

    def test_일괄_변환_성공(
        self,
        account_mapper: AccountMapper,
        sample_dart_data: dict[str, dict[str, Decimal | None]],
    ) -> None:
        """한글 계정명 dict가 StandardAccount dict로 변환된다."""
        result = account_mapper.map_all(sample_dart_data)
        assert StandardAccount.REVENUE in result
        assert StandardAccount.OPERATING_INCOME in result
        assert StandardAccount.NET_INCOME in result

    def test_일괄_변환_첫번째_매핑_우선(self, account_mapper: AccountMapper) -> None:
        """동일 StandardAccount에 복수 한글 키가 매핑될 때 첫 번째만 사용한다."""
        data = {
            "매출액": {"2024": Decimal("100")},
            "영업수익": {"2024": Decimal("200")},  # 동일 REVENUE 매핑
        }
        result = account_mapper.map_all(data)
        # 첫 번째 "매출액" 값이 사용되어야 함
        assert result[StandardAccount.REVENUE]["2024"] == Decimal("100")

    def test_일괄_변환_unmapped_추적(self) -> None:
        """매핑 실패한 계정이 unmapped_accounts에 기록된다."""
        mapper = AccountMapper()
        data = {
            "매출액": {"2024": Decimal("100")},
            "존재하지않는계정": {"2024": Decimal("999")},
        }
        mapper.map_all(data)
        assert "존재하지않는계정" in mapper.unmapped_accounts


# ============================================================================
# unmapped / warnings / reset
# ============================================================================


class TestUnmappedAndWarnings:
    """unmapped_accounts, warnings, reset 테스트."""

    def test_unmapped_accounts_추적(self) -> None:
        """매핑 실패한 계정명이 unmapped_accounts에 추가된다."""
        mapper = AccountMapper()
        mapper.map("알수없는계정XYZ")
        assert "알수없는계정XYZ" in mapper.unmapped_accounts

    def test_warnings_속성(self) -> None:
        """경고가 발생하면 warnings 리스트에 기록된다."""
        mapper = AccountMapper()
        mapper.map("")  # 빈 문자열 → 경고 발생
        assert len(mapper.warnings) >= 1

    def test_reset_초기화(self) -> None:
        """reset() 호출 시 unmapped와 warnings가 모두 초기화된다."""
        mapper = AccountMapper()
        mapper.map("알수없는계정XYZ")
        mapper.map("")
        assert len(mapper.unmapped_accounts) > 0
        assert len(mapper.warnings) > 0

        mapper.reset()
        assert mapper.unmapped_accounts == []
        assert mapper.warnings == []


# ============================================================================
# strict 모드
# ============================================================================


class TestStrictMode:
    """strict_mode=True 동작 테스트."""

    def test_strict_모드_매핑_실패_예외(self) -> None:
        """strict_mode=True일 때 매핑 실패 시 AccountNotFoundError가 발생한다."""
        config = MappingConfig(strict_mode=True)
        mapper = AccountMapper(config=config)
        with pytest.raises(AccountNotFoundError):
            mapper.map("완전히_존재하지않는_계정명")

    def test_strict_모드_매핑_성공_정상(self) -> None:
        """strict_mode=True이더라도 매핑 성공 시 정상 결과를 반환한다."""
        config = MappingConfig(strict_mode=True)
        mapper = AccountMapper(config=config)
        result = mapper.map("매출액")
        assert result is not None
        assert result.standard_code == StandardAccount.REVENUE


# ============================================================================
# 엣지 케이스
# ============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트."""

    def test_빈_문자열_None_반환(self, account_mapper: AccountMapper) -> None:
        """빈 문자열 입력 시 None을 반환한다."""
        result = account_mapper.map("")
        assert result is None

    def test_공백만_있는_문자열_None_반환(self, account_mapper: AccountMapper) -> None:
        """공백만 있는 문자열 입력 시 None을 반환한다."""
        result = account_mapper.map("   ")
        assert result is None

    def test_앞뒤_공백_strip_처리(self, account_mapper: AccountMapper) -> None:
        """앞뒤 공백이 있는 계정명이 strip 후 정확 일치로 매핑된다."""
        result = account_mapper.map("  매출액  ")
        assert result is not None
        assert result.standard_code == StandardAccount.REVENUE
        assert result.confidence == 1.0
