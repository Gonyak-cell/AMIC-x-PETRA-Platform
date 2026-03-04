"""HealthcareModule 테스트."""

from src.industry.healthcare import HealthcareModule
from src.industry.models import (
    IndustryChartRecommendation,
    IndustryContext,
    IndustryKPI,
    RiskCategory,
)
from src.industry.registry import get_industry_module
from src.narrative_generator.prompts.industry_variants.healthcare import (
    HealthcareVariant,
)


class TestHealthcareModule:
    """HealthcareModule 단위 테스트."""

    def test_registered_in_registry(self):
        """get_industry_module('healthcare') → HealthcareModule 인스턴스."""
        module = get_industry_module("healthcare")
        assert isinstance(module, HealthcareModule)

    def test_industry_id(self):
        """industry_id == 'healthcare'."""
        module = HealthcareModule()
        assert module.industry_id == "healthcare"
        assert module.industry_name_kr == "헬스케어/바이오"
        assert module.industry_name_en == "Healthcare"

    def test_kpis_count(self):
        """KPI 8개 반환."""
        module = HealthcareModule()
        kpis = module.get_kpis()
        assert len(kpis) == 8

    def test_kpis_required_ids(self):
        """필수 KPI ID가 포함되어 있다."""
        module = HealthcareModule()
        kpi_ids = {kpi.kpi_id for kpi in module.get_kpis()}
        expected = {"pipeline_count", "rnpv", "phase3_success", "rd_ratio"}
        assert expected.issubset(kpi_ids)

    def test_kpis_all_valid_structure(self):
        """모든 KPI가 IndustryKPI 인스턴스이고 필수 필드가 있다."""
        module = HealthcareModule()
        for kpi in module.get_kpis():
            assert isinstance(kpi, IndustryKPI)
            assert kpi.kpi_id
            assert kpi.name_kr
            assert kpi.name_en

    def test_financial_weights_sum(self):
        """재무 가중치 합이 1.0."""
        module = HealthcareModule()
        weights = module.get_financial_weights()
        assert len(weights) > 0
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_chart_recommendations_count(self):
        """추천 차트 5개 반환."""
        module = HealthcareModule()
        charts = module.get_chart_recommendations()
        assert len(charts) == 5
        assert all(isinstance(c, IndustryChartRecommendation) for c in charts)

    def test_narrative_variant_type(self):
        """get_narrative_variant() → HealthcareVariant."""
        module = HealthcareModule()
        variant = module.get_narrative_variant()
        assert isinstance(variant, HealthcareVariant)

    def test_risk_categories_count(self):
        """리스크 카테고리 4개 반환."""
        module = HealthcareModule()
        risks = module.get_risk_categories()
        assert len(risks) == 4
        assert all(isinstance(r, RiskCategory) for r in risks)

    def test_get_context_complete(self):
        """get_context() → 모든 필드가 비어있지 않다."""
        module = HealthcareModule()
        ctx = module.get_context()
        assert isinstance(ctx, IndustryContext)
        assert ctx.industry_id == "healthcare"
        assert len(ctx.kpis) == 8
        assert len(ctx.financial_weights) > 0
        assert len(ctx.chart_recommendations) == 5
        assert len(ctx.risk_categories) == 4
