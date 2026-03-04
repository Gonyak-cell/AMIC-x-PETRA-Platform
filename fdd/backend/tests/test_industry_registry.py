"""Industry Registry 단위 테스트 — Phase 6.

산업 모듈 레지스트리 함수들이 올바르게 동작하는지 검증.
DB 불필요 (순수 단위 테스트).
"""

import dataclasses

import pytest

from app.industry import (
    get_fdd_industry_module,
    get_fdd_industry_module_safe,
    list_industries,
)
from app.industry.base import FDDIndustryModule

EXPECTED_INDUSTRY_IDS = [
    "general",
    "tech",
    "healthcare",
    "manufacturing",
    "financial_services",
    "logistics",
]


class TestListIndustries:
    """list_industries() 테스트."""

    def test_returns_all_six(self):
        """6개 산업 모듈이 등록되어야 한다."""
        result = list_industries()
        assert len(result) == 6

    def test_each_entry_has_required_keys(self):
        """각 항목에 id, name_kr, name_en 키가 있어야 한다."""
        result = list_industries()
        for entry in result:
            assert "id" in entry
            assert "name_kr" in entry
            assert "name_en" in entry

    def test_all_expected_ids_present(self):
        """expected 6개 산업 ID가 모두 존재해야 한다."""
        result = list_industries()
        ids = {entry["id"] for entry in result}
        for expected_id in EXPECTED_INDUSTRY_IDS:
            assert expected_id in ids, f"Missing industry: {expected_id}"


class TestGetFddIndustryModule:
    """get_fdd_industry_module() — strict 모드 테스트."""

    @pytest.mark.parametrize("industry_id", EXPECTED_INDUSTRY_IDS)
    def test_get_each_valid_module(self, industry_id: str):
        """등록된 산업 ID는 모듈을 반환해야 한다."""
        module = get_fdd_industry_module(industry_id)
        assert isinstance(module, FDDIndustryModule)
        assert module.industry_id == industry_id

    def test_unknown_raises_key_error(self):
        """등록되지 않은 산업 ID는 KeyError를 발생시켜야 한다."""
        with pytest.raises(KeyError, match="지원하지 않는 FDD 산업"):
            get_fdd_industry_module("nonexistent_industry")


class TestGetFddIndustryModuleSafe:
    """get_fdd_industry_module_safe() — 폴백 모드 테스트."""

    def test_valid_id_returns_module(self):
        """등록된 산업 ID는 해당 모듈을 반환해야 한다."""
        module = get_fdd_industry_module_safe("tech")
        assert module.industry_id == "tech"

    def test_unknown_falls_back_to_general(self):
        """등록되지 않은 산업 ID는 general로 폴백해야 한다."""
        module = get_fdd_industry_module_safe("nonexistent_industry")
        assert module.industry_id == "general"


class TestIndustryModuleContext:
    """각 산업 모듈의 get_context() 호출 테스트."""

    @pytest.mark.parametrize("industry_id", EXPECTED_INDUSTRY_IDS)
    def test_get_context_returns_valid_object(self, industry_id: str):
        """모든 산업 모듈의 get_context()가 유효한 객체를 반환해야 한다."""
        module = get_fdd_industry_module(industry_id)
        ctx = module.get_context()
        assert ctx is not None
        # FDDIndustryContext should have adjustment_rules at minimum
        assert hasattr(ctx, "adjustment_rules")
        assert hasattr(ctx, "nwc_norms")
        assert hasattr(ctx, "debt_classifications")

    @pytest.mark.parametrize("industry_id", EXPECTED_INDUSTRY_IDS)
    def test_context_has_non_empty_rules(self, industry_id: str):
        """모든 산업 모듈의 context 필드가 비어있지 않아야 한다."""
        module = get_fdd_industry_module(industry_id)
        ctx = module.get_context()
        assert len(ctx.adjustment_rules) > 0, f"{industry_id}: adjustment_rules empty"
        assert len(ctx.nwc_norms) > 0, f"{industry_id}: nwc_norms empty"
        assert len(ctx.debt_classifications) > 0, (
            f"{industry_id}: debt_classifications empty"
        )
        assert len(ctx.kpi_benchmarks) > 0, f"{industry_id}: kpi_benchmarks empty"

    @pytest.mark.parametrize("industry_id", EXPECTED_INDUSTRY_IDS)
    def test_narrative_templates_returns_list(self, industry_id: str):
        """모든 산업 모듈의 get_narrative_templates()가 list를 반환해야 한다."""
        module = get_fdd_industry_module(industry_id)
        result = module.get_narrative_templates()
        assert isinstance(result, list)

    def test_context_frozen_dataclass_immutability(self):
        """FDDAdjustmentRule 등 frozen dataclass는 수정 불가능해야 한다."""
        module = get_fdd_industry_module("general")
        ctx = module.get_context()
        rule = ctx.adjustment_rules[0]
        with pytest.raises(dataclasses.FrozenInstanceError):
            rule.rule_id = "tampered"
