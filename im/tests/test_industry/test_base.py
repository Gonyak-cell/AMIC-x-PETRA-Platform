"""산업 모듈 기반 클래스 테스트."""

import pytest

from src.industry.base import IndustryModule
from src.industry.models import IndustryContext, IndustryKPI

from tests.test_industry.conftest import DummyIndustryModule


class TestIndustryModuleABC:
    """IndustryModule 추상 기반 클래스."""

    def test_industry_module_abstract(self):
        """IndustryModule 직접 인스턴스화 불가 (TypeError)."""
        with pytest.raises(TypeError):
            IndustryModule()  # type: ignore[abstract]

    def test_dummy_module_get_kpis(self, dummy_module: DummyIndustryModule):
        """DummyModule.get_kpis() 반환 타입/내용 검증."""
        kpis = dummy_module.get_kpis()
        assert isinstance(kpis, list)
        assert len(kpis) == 1
        assert isinstance(kpis[0], IndustryKPI)
        assert kpis[0].kpi_id == "test_kpi"
        assert kpis[0].name_kr == "테스트 KPI"

    def test_dummy_module_get_context(self, dummy_module: DummyIndustryModule):
        """DummyModule.get_context() → IndustryContext 필드 채워짐."""
        ctx = dummy_module.get_context()
        assert isinstance(ctx, IndustryContext)
        assert ctx.industry_id == "dummy"
        assert ctx.industry_name_kr == "더미"
        assert ctx.industry_name_en == "Dummy"
        assert len(ctx.kpis) == 1
        assert ctx.financial_weights == {"revenue_growth": 0.8, "ebitda_margin": 0.5}
        assert len(ctx.chart_recommendations) == 1
        assert len(ctx.risk_categories) == 1
