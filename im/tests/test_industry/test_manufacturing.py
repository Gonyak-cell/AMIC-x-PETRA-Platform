"""ManufacturingModule 테스트."""

from src.industry.manufacturing import ManufacturingModule
from src.industry.models import (
    IndustryChartRecommendation,
    IndustryContext,
    IndustryKPI,
    RiskCategory,
)
from src.industry.registry import get_industry_module
from src.narrative_generator.prompts.industry_variants.manufacturing import (
    ManufacturingVariant,
)


class TestManufacturingModule:
    """ManufacturingModule 단위 테스트."""

    def test_registered_in_registry(self):
        """get_industry_module('manufacturing') → ManufacturingModule 인스턴스."""
        module = get_industry_module("manufacturing")
        assert isinstance(module, ManufacturingModule)

    def test_industry_id(self):
        """industry_id == 'manufacturing'."""
        module = ManufacturingModule()
        assert module.industry_id == "manufacturing"
        assert module.industry_name_kr == "제조업"
        assert module.industry_name_en == "Manufacturing"

    def test_kpis_count(self):
        """KPI 8개 반환."""
        module = ManufacturingModule()
        kpis = module.get_kpis()
        assert len(kpis) == 8

    def test_kpis_required_ids(self):
        """필수 KPI ID가 포함되어 있다."""
        module = ManufacturingModule()
        kpi_ids = {kpi.kpi_id for kpi in module.get_kpis()}
        expected = {"oee", "capacity_util", "yield_rate", "cogs_ratio", "capex_ratio"}
        assert expected.issubset(kpi_ids)

    def test_kpis_all_valid_structure(self):
        """모든 KPI가 IndustryKPI 인스턴스이고 필수 필드가 있다."""
        module = ManufacturingModule()
        for kpi in module.get_kpis():
            assert isinstance(kpi, IndustryKPI)
            assert kpi.kpi_id
            assert kpi.name_kr
            assert kpi.name_en

    def test_financial_weights_sum(self):
        """재무 가중치 합이 1.0."""
        module = ManufacturingModule()
        weights = module.get_financial_weights()
        assert len(weights) > 0
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_chart_recommendations_count(self):
        """추천 차트 5개 반환."""
        module = ManufacturingModule()
        charts = module.get_chart_recommendations()
        assert len(charts) == 5
        assert all(isinstance(c, IndustryChartRecommendation) for c in charts)

    def test_narrative_variant_type(self):
        """get_narrative_variant() → ManufacturingVariant."""
        module = ManufacturingModule()
        variant = module.get_narrative_variant()
        assert isinstance(variant, ManufacturingVariant)

    def test_risk_categories_count(self):
        """리스크 카테고리 4개 반환."""
        module = ManufacturingModule()
        risks = module.get_risk_categories()
        assert len(risks) == 4
        assert all(isinstance(r, RiskCategory) for r in risks)

    def test_get_context_complete(self):
        """get_context() → 모든 필드가 비어있지 않다."""
        module = ManufacturingModule()
        ctx = module.get_context()
        assert isinstance(ctx, IndustryContext)
        assert ctx.industry_id == "manufacturing"
        assert len(ctx.kpis) == 8
        assert len(ctx.financial_weights) > 0
        assert len(ctx.chart_recommendations) == 5
        assert len(ctx.risk_categories) == 4
