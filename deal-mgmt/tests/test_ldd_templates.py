"""LDD 거래유형별 템플릿 시스템 테스트."""

import pytest

from app.ralph.generators.ldd.templates import TemplateRegistry
from app.ralph.generators.ldd.templates.asset_acquisition import AssetAcquisitionTemplate
from app.ralph.generators.ldd.templates.base import ItemDef, LDDTemplate, SectionDef
from app.ralph.generators.ldd.templates.corporate_split import CorporateSplitTemplate
from app.ralph.generators.ldd.templates.ipo import IPOTemplate
from app.ralph.generators.ldd.templates.preferred_stock import PreferredStockTemplate
from app.ralph.generators.ldd.templates.real_estate import RealEstateTemplate
from app.ralph.generators.ldd.templates.stock_acquisition import StockAcquisitionTemplate

# ── TemplateRegistry 테스트 ────────────────────────────────────────────────────


class TestTemplateRegistry:
    """TemplateRegistry 핵심 동작 검증."""

    def test_get_stock_acquisition(self):
        t = TemplateRegistry.get("STOCK_ACQUISITION")
        assert t is not None
        assert isinstance(t, StockAcquisitionTemplate)
        assert t.display_name == "주식인수"

    def test_get_real_estate(self):
        t = TemplateRegistry.get("REAL_ESTATE")
        assert t is not None
        assert isinstance(t, RealEstateTemplate)

    def test_get_ipo(self):
        t = TemplateRegistry.get("IPO")
        assert t is not None
        assert isinstance(t, IPOTemplate)

    def test_get_corporate_split(self):
        t = TemplateRegistry.get("CORPORATE_SPLIT")
        assert t is not None
        assert isinstance(t, CorporateSplitTemplate)

    def test_get_preferred_stock(self):
        t = TemplateRegistry.get("PREFERRED_STOCK")
        assert t is not None
        assert isinstance(t, PreferredStockTemplate)

    def test_get_asset_acquisition(self):
        t = TemplateRegistry.get("ASSET_ACQUISITION")
        assert t is not None
        assert isinstance(t, AssetAcquisitionTemplate)

    def test_get_unknown_returns_none(self):
        t = TemplateRegistry.get("UNKNOWN_TYPE")
        assert t is None

    def test_get_or_default_empty_string_returns_none(self):
        t = TemplateRegistry.get_or_default("")
        assert t is None

    def test_get_or_default_valid_type(self):
        t = TemplateRegistry.get_or_default("IPO")
        assert t is not None
        assert isinstance(t, IPOTemplate)

    def test_get_sections_dict_returns_none_for_empty(self):
        result = TemplateRegistry.get_sections_dict("")
        assert result is None

    def test_get_sections_dict_returns_list_for_valid_type(self):
        result = TemplateRegistry.get_sections_dict("STOCK_ACQUISITION")
        assert isinstance(result, list)
        assert len(result) == 11  # 주식인수는 11개 섹션

    def test_list_deal_types(self):
        types = TemplateRegistry.list_deal_types()
        assert len(types) == 6
        names = {t["deal_type"] for t in types}
        assert "STOCK_ACQUISITION" in names
        assert "IPO" in names

    def test_register_custom_template(self):
        class CustomTemplate(LDDTemplate):
            deal_type = "CUSTOM_TEST"
            display_name = "커스텀 테스트"
            sections = [SectionDef("TEST", "테스트", [ItemDef("T-01", "테스트 항목")])]

        TemplateRegistry.register("CUSTOM_TEST", CustomTemplate)
        t = TemplateRegistry.get("CUSTOM_TEST")
        assert t is not None
        assert t.display_name == "커스텀 테스트"
        # 정리
        TemplateRegistry._templates.pop("CUSTOM_TEST", None)


# ── 섹션 구조 검증 ──────────────────────────────────────────────────────────────


class TestSectionStructure:
    """각 템플릿의 섹션 구조가 올바른지 검증."""

    @pytest.mark.parametrize(
        "deal_type, expected_sections, expected_min_items",
        [
            ("STOCK_ACQUISITION", 11, 55),
            ("REAL_ESTATE", 6, 25),
            ("IPO", 4, 20),
            ("CORPORATE_SPLIT", 8, 30),
            ("PREFERRED_STOCK", 9, 35),
            ("ASSET_ACQUISITION", 10, 35),
        ],
    )
    def test_section_count_and_items(self, deal_type, expected_sections, expected_min_items):
        t = TemplateRegistry.get(deal_type)
        assert t is not None
        assert len(t.sections) == expected_sections
        assert t.get_item_count() >= expected_min_items

    @pytest.mark.parametrize("deal_type", [
        "STOCK_ACQUISITION", "REAL_ESTATE", "IPO",
        "CORPORATE_SPLIT", "PREFERRED_STOCK", "ASSET_ACQUISITION",
    ])
    def test_sections_dict_format(self, deal_type):
        """get_sections_dict()가 DEFAULT_LDD_SECTIONS와 동일한 형식을 반환하는지 검증."""
        sections = TemplateRegistry.get_sections_dict(deal_type)
        assert isinstance(sections, list)
        for section in sections:
            assert "section_type" in section
            assert "title" in section
            assert "items" in section
            assert isinstance(section["items"], list)
            for item in section["items"]:
                assert "item_id" in item
                assert "name" in item
                assert "status" in item
                assert item["status"] == "PENDING"
                assert "issue_level" in item
                assert "risk_color" in item
                assert "description" in item
                assert "deal_impact" in item
                assert "recommendation" in item
                assert "rfi_required" in item
                assert "evidence_refs" in item

    @pytest.mark.parametrize("deal_type", [
        "STOCK_ACQUISITION", "REAL_ESTATE", "IPO",
        "CORPORATE_SPLIT", "PREFERRED_STOCK", "ASSET_ACQUISITION",
    ])
    def test_unique_item_ids(self, deal_type):
        """각 템플릿 내 item_id가 고유한지 검증."""
        t = TemplateRegistry.get(deal_type)
        all_ids = []
        for section in t.sections:
            for item in section.items:
                all_ids.append(item.item_id)
        assert len(all_ids) == len(set(all_ids)), f"중복 item_id 발견: {deal_type}"

    @pytest.mark.parametrize("deal_type", [
        "STOCK_ACQUISITION", "REAL_ESTATE", "IPO",
        "CORPORATE_SPLIT", "PREFERRED_STOCK", "ASSET_ACQUISITION",
    ])
    def test_unique_section_types(self, deal_type):
        """각 템플릿 내 section_type이 고유한지 검증."""
        t = TemplateRegistry.get(deal_type)
        types = [s.section_type for s in t.sections]
        assert len(types) == len(set(types)), f"중복 section_type 발견: {deal_type}"


# ── _resolve_sections 테스트 ─────────────────────────────────────────────────


class TestResolveSections:
    """서비스 계층의 _resolve_sections 헬퍼 검증."""

    def test_explicit_sections_override(self):
        from app.services.ldd_report_service import _resolve_sections
        explicit = [{"section_type": "CUSTOM", "title": "커스텀", "items": []}]
        sections, ttype = _resolve_sections("STOCK_ACQUISITION", explicit)
        assert sections == explicit
        assert ttype == "CUSTOM"

    def test_deal_type_template(self):
        from app.services.ldd_report_service import _resolve_sections
        sections, ttype = _resolve_sections("IPO")
        assert ttype == "IPO"
        assert len(sections) == 4

    def test_empty_deal_type_fallback(self):
        from app.schemas.ldd_report import DEFAULT_LDD_SECTIONS
        from app.services.ldd_report_service import _resolve_sections
        sections, ttype = _resolve_sections("")
        assert ttype == "DEFAULT"
        assert len(sections) == len(DEFAULT_LDD_SECTIONS)

    def test_unknown_deal_type_fallback(self):
        from app.services.ldd_report_service import _resolve_sections
        sections, ttype = _resolve_sections("NONEXISTENT")
        assert ttype == "DEFAULT"
