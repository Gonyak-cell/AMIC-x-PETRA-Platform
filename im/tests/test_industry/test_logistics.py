"""LogisticsModule 테스트."""


from src.industry.logistics import LogisticsModule
from src.industry.models import (
    IndustryChartRecommendation,
    IndustryContext,
    IndustryKPI,
    RiskCategory,
)
from src.industry.registry import get_industry_module
from src.narrative_generator.prompts.industry_variants.logistics import (
    LogisticsVariant,
)


class TestLogisticsModule:
    """LogisticsModule 단위 테스트."""

    def test_registered_in_registry(self):
        """get_industry_module('logistics') → LogisticsModule 인스턴스."""
        module = get_industry_module("logistics")
        assert isinstance(module, LogisticsModule)

    def test_industry_id(self):
        """industry_id == 'logistics'."""
        module = LogisticsModule()
        assert module.industry_id == "logistics"
        assert module.industry_name_kr == "물류/운송"
        assert module.industry_name_en == "Logistics"

    def test_kpis_count(self):
        """KPI 8개 반환."""
        module = LogisticsModule()
        kpis = module.get_kpis()
        assert len(kpis) == 8

    def test_kpis_required_ids(self):
        """필수 KPI ID가 포함되어 있다."""
        module = LogisticsModule()
        kpi_ids = {kpi.kpi_id for kpi in module.get_kpis()}
        expected = {"otd", "fleet_util", "rev_per_tonkm", "warehouse_util", "claims_ratio"}
        assert expected.issubset(kpi_ids)

    def test_kpis_all_valid_structure(self):
        """모든 KPI가 IndustryKPI 인스턴스이고 필수 필드가 있다."""
        module = LogisticsModule()
        for kpi in module.get_kpis():
            assert isinstance(kpi, IndustryKPI)
            assert kpi.kpi_id
            assert kpi.name_kr
            assert kpi.name_en

    def test_financial_weights_sum(self):
        """재무 가중치 합이 1.0."""
        module = LogisticsModule()
        weights = module.get_financial_weights()
        assert len(weights) > 0
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_chart_recommendations_count(self):
        """추천 차트 5개 반환."""
        module = LogisticsModule()
        charts = module.get_chart_recommendations()
        assert len(charts) == 5
        assert all(isinstance(c, IndustryChartRecommendation) for c in charts)

    def test_narrative_variant_type(self):
        """get_narrative_variant() → LogisticsVariant."""
        module = LogisticsModule()
        variant = module.get_narrative_variant()
        assert isinstance(variant, LogisticsVariant)

    def test_risk_categories_count(self):
        """리스크 카테고리 4개 반환."""
        module = LogisticsModule()
        risks = module.get_risk_categories()
        assert len(risks) == 4
        assert all(isinstance(r, RiskCategory) for r in risks)

    def test_get_context_complete(self):
        """get_context() → 모든 필드가 비어있지 않다."""
        module = LogisticsModule()
        ctx = module.get_context()
        assert isinstance(ctx, IndustryContext)
        assert ctx.industry_id == "logistics"
        assert len(ctx.kpis) == 8
        assert len(ctx.financial_weights) > 0
        assert len(ctx.chart_recommendations) == 5
        assert len(ctx.risk_categories) == 4
