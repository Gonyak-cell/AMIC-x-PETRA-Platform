"""LogisticsVariant 테스트."""

from src.narrative_generator.prompts import INDUSTRY_VARIANTS, get_industry_variant
from src.narrative_generator.prompts.industry_variants.logistics import (
    LogisticsVariant,
)


class TestLogisticsVariant:
    """LogisticsVariant 단위 테스트."""

    def test_config_industry_id(self):
        """config.industry_id == 'logistics'."""
        variant = LogisticsVariant()
        assert variant.config.industry_id == "logistics"
        assert variant.config.industry_name_kr == "물류/운송"
        assert variant.config.industry_name_en == "Logistics"

    def test_industry_context_not_empty(self):
        """get_industry_context()가 비어있지 않은 문자열."""
        variant = LogisticsVariant()
        context = variant.get_industry_context()
        assert isinstance(context, str)
        assert len(context) > 50
        assert "물동량" in context or "물류" in context

    def test_terminology_overrides_keys(self):
        """용어 오버라이드에 4개 키가 존재한다."""
        variant = LogisticsVariant()
        overrides = variant.get_terminology_overrides()
        assert isinstance(overrides, dict)
        assert len(overrides) == 4
        assert "매출액" in overrides
        assert "고객 수" in overrides

    def test_emphasis_areas_count(self):
        """강조 영역 6개 반환."""
        variant = LogisticsVariant()
        areas = variant.get_emphasis_areas()
        assert isinstance(areas, list)
        assert len(areas) == 6

    def test_registered_in_industry_variants(self):
        """INDUSTRY_VARIANTS['logistics']에 등록됨."""
        assert "logistics" in INDUSTRY_VARIANTS
        variant = get_industry_variant("logistics")
        assert isinstance(variant, LogisticsVariant)
