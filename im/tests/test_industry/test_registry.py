"""산업 모듈 레지스트리 테스트."""

import pytest

from src.industry.base import IndustryModule
from src.industry.exceptions import UnsupportedIndustryError
from src.industry.models import IndustryChartRecommendation, IndustryKPI
from src.industry.registry import (
    INDUSTRY_REGISTRY,
    get_industry_module,
    register_industry,
)

from .conftest import DummyIndustryModule


class TestRegisterIndustry:
    """@register_industry 데코레이터."""

    def test_register_industry_decorator(self):
        """@register_industry로 모듈 등록 후 REGISTRY에 존재."""
        register_industry(DummyIndustryModule)
        assert "dummy" in INDUSTRY_REGISTRY
        assert INDUSTRY_REGISTRY["dummy"] is DummyIndustryModule

    def test_register_multiple_industries(self):
        """복수 산업 모듈 등록 후 각각 조회 성공."""

        class AnotherModule(IndustryModule):
            industry_id = "another"
            industry_name_kr = "다른산업"
            industry_name_en = "Another"

            def get_kpis(self) -> list[IndustryKPI]:
                return []

            def get_financial_weights(self) -> dict[str, float]:
                return {}

            def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
                return []

            def get_narrative_variant(self):  # type: ignore[override]
                return None

        register_industry(DummyIndustryModule)
        register_industry(AnotherModule)

        assert "dummy" in INDUSTRY_REGISTRY
        assert "another" in INDUSTRY_REGISTRY


class TestGetIndustryModule:
    """get_industry_module() 조회 함수."""

    def test_get_industry_module_success(self):
        """등록된 industry_id로 조회 성공."""
        register_industry(DummyIndustryModule)
        module = get_industry_module("dummy")
        assert module is not None
        assert module.industry_id == "dummy"

    def test_get_industry_module_returns_instance(self):
        """반환값이 IndustryModule 인스턴스."""
        register_industry(DummyIndustryModule)
        module = get_industry_module("dummy")
        assert isinstance(module, IndustryModule)
        assert isinstance(module, DummyIndustryModule)

    def test_get_industry_module_unknown_raises(self):
        """미등록 industry_id → UnsupportedIndustryError."""
        with pytest.raises(UnsupportedIndustryError) as exc_info:
            get_industry_module("nonexistent")
        assert exc_info.value.industry_id == "nonexistent"
