"""산업 모듈 데이터 모델 테스트."""

import pytest

from src.industry.models import (
    IndustryChartRecommendation,
    IndustryContext,
    IndustryKPI,
    KPIUnit,
    RiskCategory,
)


class TestIndustryKPI:
    """IndustryKPI 데이터클래스."""

    def test_industry_kpi_creation(self):
        """IndustryKPI 생성 및 필드 검증."""
        kpi = IndustryKPI(
            kpi_id="arr",
            name_kr="연간 반복 매출",
            name_en="Annual Recurring Revenue",
            unit=KPIUnit.CURRENCY_KRW,
            description="SaaS 핵심 지표",
            formula="MRR × 12",
            display_format="{:,.0f}억원",
            higher_is_better=True,
            benchmark_range=(100.0, 500.0),
        )
        assert kpi.kpi_id == "arr"
        assert kpi.name_kr == "연간 반복 매출"
        assert kpi.unit == KPIUnit.CURRENCY_KRW
        assert kpi.benchmark_range == (100.0, 500.0)
        assert kpi.higher_is_better is True

    def test_industry_kpi_frozen(self):
        """IndustryKPI는 수정 불가 (frozen=True)."""
        kpi = IndustryKPI(
            kpi_id="nrr",
            name_kr="순매출유지율",
            name_en="Net Revenue Retention",
        )
        with pytest.raises(AttributeError):
            kpi.kpi_id = "changed"  # type: ignore[misc]


class TestIndustryChartRecommendation:
    """IndustryChartRecommendation 데이터클래스."""

    def test_industry_chart_recommendation(self):
        """IndustryChartRecommendation 생성 + 기본값 확인."""
        rec = IndustryChartRecommendation(
            chart_type="combo",
            title_template="{company_name} ARR 추이",
            target_section="financial_analysis",
        )
        assert rec.chart_type == "combo"
        assert rec.target_section == "financial_analysis"
        assert rec.data_keys == []
        assert rec.priority == 1
        assert rec.description == ""


class TestIndustryContext:
    """IndustryContext 데이터클래스."""

    def test_industry_context_defaults(self):
        """IndustryContext 기본값 검증."""
        ctx = IndustryContext()
        assert ctx.industry_id == ""
        assert ctx.industry_name_kr == ""
        assert ctx.kpis == []
        assert ctx.financial_weights == {}
        assert ctx.chart_recommendations == []
        assert ctx.risk_categories == []
        assert ctx.extra == {}


class TestRiskCategory:
    """RiskCategory 데이터클래스."""

    def test_risk_category_creation(self):
        """RiskCategory 생성 + risk_factors 리스트 확인."""
        risk = RiskCategory(
            category_id="regulatory",
            name_kr="규제 리스크",
            name_en="Regulatory Risk",
            description="산업 규제 변동 리스크",
            risk_factors=["신규 규제 도입", "라이선스 변경"],
        )
        assert risk.category_id == "regulatory"
        assert len(risk.risk_factors) == 2
        assert "신규 규제 도입" in risk.risk_factors
