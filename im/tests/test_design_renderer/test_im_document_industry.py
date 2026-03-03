"""IMDocumentData 산업 모듈 통합 테스트."""

from src.design_renderer.im_document import (
    ALL_SECTION_IDS,
    INDUSTRY_SECTION_IDS,
    SECTION_IDS,
    IMDocumentData,
    IMStyle,
)


class TestIndustrySectionIDs:
    """산업별 섹션 ID 상수."""

    def test_industry_section_ids_defined(self):
        """INDUSTRY_SECTION_IDS, ALL_SECTION_IDS 존재 확인."""
        assert "industry_kpi" in INDUSTRY_SECTION_IDS
        assert "industry_overview" in INDUSTRY_SECTION_IDS
        assert len(INDUSTRY_SECTION_IDS) == 2
        # ALL = IM(19) + TM(8) + DM(6) + Industry(2) = 35
        assert len(ALL_SECTION_IDS) == 35

    def test_base_section_ids_unchanged(self):
        """기존 SECTION_IDS는 19개 (valuation 추가)."""
        assert len(SECTION_IDS) == 19
        assert "industry_kpi" not in SECTION_IDS
        assert "industry_overview" not in SECTION_IDS


class TestGetActiveSectionsIndustry:
    """산업 모듈 활성화 시 get_active_sections() 동작."""

    def test_get_active_sections_no_industry(self):
        """industry="" → 기존 동작 동일 (산업 섹션 미포함)."""
        data = IMDocumentData(im_style=IMStyle.FULL)
        active = data.get_active_sections()
        assert len(active) == 19
        assert "industry_kpi" not in active
        assert "industry_overview" not in active

    def test_get_active_sections_with_industry(self):
        """industry="tech" → industry_kpi, industry_overview 자동 삽입."""
        data = IMDocumentData(im_style=IMStyle.FULL, industry="tech")
        active = data.get_active_sections()
        assert "industry_kpi" in active
        assert "industry_overview" in active
        assert len(active) == 21

    def test_get_active_sections_industry_position(self):
        """산업 섹션이 financial_analysis 바로 뒤에 위치."""
        data = IMDocumentData(im_style=IMStyle.FULL, industry="tech")
        active = data.get_active_sections()
        fa_idx = active.index("financial_analysis")
        assert active[fa_idx + 1] == "industry_kpi"
        assert active[fa_idx + 2] == "industry_overview"

    def test_titan_with_industry(self):
        """TITAN + industry → 산업 섹션 추가."""
        data = IMDocumentData(im_style=IMStyle.TITAN, industry="manufacturing")
        active = data.get_active_sections()
        assert "industry_kpi" in active
        assert "industry_overview" in active
        # TITAN 기본 9 + 산업 2 = 11
        assert len(active) == 11
