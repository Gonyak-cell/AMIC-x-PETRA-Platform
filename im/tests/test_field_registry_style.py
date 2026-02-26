"""스타일별 필드 필터링 테스트.

get_fields_for_style()이 각 IM 스타일에 맞는 필드 수를 반환하는지 검증한다.
"""

from __future__ import annotations

import pytest

from src.api.services.checklist_field_registry import (
    get_all_fields,
    get_fields_for_style,
)


class TestGetFieldsForStyle:
    """get_fields_for_style() 단위 테스트."""

    def test_full_returns_all_80(self) -> None:
        """FULL 스타일은 전체 80필드를 반환한다."""
        fields = get_fields_for_style("FULL")
        assert len(fields) == 80

    def test_custom_returns_all_80(self) -> None:
        """CUSTOM 스타일도 전체 80필드를 반환한다."""
        assert len(get_fields_for_style("CUSTOM")) == 80

    def test_titan_returns_all_80(self) -> None:
        """TITAN 스타일도 전체 80필드를 반환한다."""
        assert len(get_fields_for_style("TITAN")) == 80

    def test_teaser_returns_40(self) -> None:
        """TEASER 스타일은 40필드를 반환한다."""
        fields = get_fields_for_style("TEASER")
        assert len(fields) == 40

    def test_tm_returns_40(self) -> None:
        """TM 스타일은 TEASER와 동일하게 40필드를 반환한다."""
        fields = get_fields_for_style("TM")
        assert len(fields) == 40

    def test_dm_returns_46(self) -> None:
        """DM 스타일은 46필드를 반환한다."""
        fields = get_fields_for_style("DM")
        assert len(fields) == 46


class TestTmFieldContent:
    """TM 필드 내용 검증."""

    def test_tm_financial_has_core_4(self) -> None:
        """TM 재무 필드는 핵심 4지표(revenue, operating_income, ebitda, net_income) × 3년 = 12개."""
        fields = get_fields_for_style("TEASER")
        fin_fields = [f for f in fields if f.category == "FINANCIAL"]
        assert len(fin_fields) == 12

        keys = {f.field_key for f in fin_fields}
        assert "revenue_2022" in keys
        assert "ebitda_2024" in keys
        assert "net_income_2023" in keys

    def test_tm_financial_excludes_non_core(self) -> None:
        """TM 재무 필드에 total_assets, cash 등은 미포함."""
        fields = get_fields_for_style("TEASER")
        keys = {f.field_key for f in fields if f.category == "FINANCIAL"}
        assert "total_assets_2024" not in keys
        assert "cash_2024" not in keys
        assert "total_debt_2024" not in keys

    def test_tm_company_has_8(self) -> None:
        """TM 회사 필드는 8개."""
        fields = get_fields_for_style("TEASER")
        assert len([f for f in fields if f.category == "COMPANY"]) == 8

    def test_tm_market_has_8(self) -> None:
        """TM 시장 필드는 8개 (전체)."""
        fields = get_fields_for_style("TEASER")
        assert len([f for f in fields if f.category == "MARKET"]) == 8

    def test_tm_deal_has_4(self) -> None:
        """TM 거래 필드는 4개."""
        fields = get_fields_for_style("TEASER")
        assert len([f for f in fields if f.category == "DEAL"]) == 4

    def test_tm_management_has_4(self) -> None:
        """TM 경영진 필드는 4개 (상위 2명)."""
        fields = get_fields_for_style("TEASER")
        assert len([f for f in fields if f.category == "MANAGEMENT"]) == 4

    def test_tm_shareholders_has_4(self) -> None:
        """TM 주주 필드는 4개 (상위 2명)."""
        fields = get_fields_for_style("TEASER")
        assert len([f for f in fields if f.category == "SHAREHOLDERS"]) == 4


class TestDmFieldContent:
    """DM 필드 내용 검증."""

    def test_dm_financial_has_core_6(self) -> None:
        """DM 재무 필드는 6지표 × 3년 = 18개."""
        fields = get_fields_for_style("DM")
        fin_fields = [f for f in fields if f.category == "FINANCIAL"]
        assert len(fin_fields) == 18

        keys = {f.field_key for f in fin_fields}
        assert "cogs_2024" in keys
        assert "gross_profit_2023" in keys

    def test_dm_company_has_6(self) -> None:
        """DM 회사 필드는 6개."""
        fields = get_fields_for_style("DM")
        assert len([f for f in fields if f.category == "COMPANY"]) == 6

    def test_dm_deal_has_10(self) -> None:
        """DM 거래 필드는 전체 10개."""
        fields = get_fields_for_style("DM")
        assert len([f for f in fields if f.category == "DEAL"]) == 10

    def test_dm_management_has_0(self) -> None:
        """DM 경영진 필드는 0개 (미포함)."""
        fields = get_fields_for_style("DM")
        assert len([f for f in fields if f.category == "MANAGEMENT"]) == 0

    def test_dm_shareholders_has_4(self) -> None:
        """DM 주주 필드는 4개."""
        fields = get_fields_for_style("DM")
        assert len([f for f in fields if f.category == "SHAREHOLDERS"]) == 4


class TestUnknownStyleFallback:
    """알 수 없는 스타일은 전체 필드 반환."""

    def test_unknown_style_returns_all(self) -> None:
        """등록되지 않은 스타일은 안전하게 전체 필드를 반환한다."""
        fields = get_fields_for_style("UNKNOWN_STYLE")
        assert len(fields) == 80

    def test_case_insensitive(self) -> None:
        """대소문자 무관하게 동작한다."""
        assert len(get_fields_for_style("teaser")) == 40
        assert len(get_fields_for_style("dm")) == 46
        assert len(get_fields_for_style("full")) == 80
