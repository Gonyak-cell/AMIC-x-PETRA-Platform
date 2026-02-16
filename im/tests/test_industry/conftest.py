"""산업 모듈 테스트 공유 픽스처."""

from __future__ import annotations

import pytest

from src.industry.base import IndustryModule
from src.industry.models import (
    IndustryChartRecommendation,
    IndustryKPI,
    KPIUnit,
    RiskCategory,
)
from src.industry.registry import INDUSTRY_REGISTRY


class DummyIndustryModule(IndustryModule):
    """테스트용 더미 산업 모듈."""

    industry_id = "dummy"
    industry_name_kr = "더미"
    industry_name_en = "Dummy"

    def get_kpis(self) -> list[IndustryKPI]:
        return [
            IndustryKPI(
                kpi_id="test_kpi",
                name_kr="테스트 KPI",
                name_en="Test KPI",
                unit=KPIUnit.PERCENTAGE,
                description="테스트용 KPI",
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        return {"revenue_growth": 0.8, "ebitda_margin": 0.5}

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        return [
            IndustryChartRecommendation(
                chart_type="combo",
                title_template="{company_name} 매출 추이",
                target_section="financial_analysis",
                data_keys=["revenue"],
            ),
        ]

    def get_narrative_variant(self):  # type: ignore[override]
        return None

    def get_risk_categories(self) -> list[RiskCategory]:
        return [
            RiskCategory(
                category_id="test_risk",
                name_kr="테스트 리스크",
                name_en="Test Risk",
                risk_factors=["리스크 요인 1"],
            ),
        ]


@pytest.fixture
def dummy_module() -> DummyIndustryModule:
    """테스트용 더미 산업 모듈."""
    return DummyIndustryModule()


@pytest.fixture(autouse=True)
def clean_registry():
    """테스트 간 레지스트리 격리."""
    original = dict(INDUSTRY_REGISTRY)
    yield
    INDUSTRY_REGISTRY.clear()
    INDUSTRY_REGISTRY.update(original)
