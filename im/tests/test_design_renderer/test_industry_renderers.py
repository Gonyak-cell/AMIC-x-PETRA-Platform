"""산업별 섹션 렌더러(IndustryKPI, IndustryOverview) 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.design_renderer.design_tokens import DEFAULT_TOKENS
from src.design_renderer.im_document import IMDocumentData
from src.design_renderer.section_renderers import RENDERER_REGISTRY, get_renderer


class TestIndustryRendererRegistration:
    """렌더러 레지스트리 등록 확인."""

    def test_industry_kpi_renderer_registered(self):
        """RENDERER_REGISTRY에 'industry_kpi' 존재."""
        assert "industry_kpi" in RENDERER_REGISTRY

    def test_industry_overview_renderer_registered(self):
        """RENDERER_REGISTRY에 'industry_overview' 존재."""
        assert "industry_overview" in RENDERER_REGISTRY

    def test_get_renderer_industry_kpi(self):
        """get_renderer('industry_kpi') → IndustryKPIRenderer 인스턴스."""
        renderer = get_renderer("industry_kpi")
        assert renderer.section_id == "industry_kpi"

    def test_get_renderer_industry_overview(self):
        """get_renderer('industry_overview') → IndustryOverviewRenderer 인스턴스."""
        renderer = get_renderer("industry_overview")
        assert renderer.section_id == "industry_overview"


@pytest.fixture
def mock_data_with_industry() -> IMDocumentData:
    """industry='tech'이 설정된 IMDocumentData mock."""
    data = MagicMock(spec=IMDocumentData)
    data.industry = "tech"
    data.industry_data = {"arr": 150, "nrr": 115.5}
    data.narratives = {"industry_overview": "테스트 산업 개요 내러티브입니다."}
    data.charts = {}
    data.number_format = MagicMock()
    return data


@pytest.fixture
def mock_data_no_industry() -> IMDocumentData:
    """industry=''인 IMDocumentData mock."""
    data = MagicMock(spec=IMDocumentData)
    data.industry = ""
    data.industry_data = {}
    data.narratives = {}
    data.charts = {}
    data.number_format = MagicMock()
    return data


class TestIndustryKPIRendererHtml:
    """IndustryKPIRenderer HTML 렌더링."""

    def test_html_with_industry(self, mock_data_with_industry: IMDocumentData):
        """industry 설정 시 HTML 슬라이드 생성."""
        renderer = get_renderer("industry_kpi")
        slides = renderer.render_html(
            mock_data_with_industry, tokens=DEFAULT_TOKENS,
        )
        assert isinstance(slides, list)
        assert len(slides) >= 1
        assert "KPI" in slides[0] or "kpi" in slides[0].lower()

    def test_html_without_industry(self, mock_data_no_industry: IMDocumentData):
        """industry 미설정 시 빈 리스트."""
        renderer = get_renderer("industry_kpi")
        slides = renderer.render_html(
            mock_data_no_industry, tokens=DEFAULT_TOKENS,
        )
        assert slides == []


class TestIndustryOverviewRendererHtml:
    """IndustryOverviewRenderer HTML 렌더링."""

    def test_html_with_industry(self, mock_data_with_industry: IMDocumentData):
        """industry 설정 시 HTML 슬라이드 생성."""
        renderer = get_renderer("industry_overview")
        slides = renderer.render_html(
            mock_data_with_industry, tokens=DEFAULT_TOKENS,
        )
        assert isinstance(slides, list)
        assert len(slides) >= 1

    def test_html_without_industry(self, mock_data_no_industry: IMDocumentData):
        """industry 미설정 시 빈 리스트."""
        renderer = get_renderer("industry_overview")
        slides = renderer.render_html(
            mock_data_no_industry, tokens=DEFAULT_TOKENS,
        )
        assert slides == []


class TestIndustryKPIRendererPptx:
    """IndustryKPIRenderer PPTX 렌더링."""

    @patch("src.design_renderer.pptx_engine.shape_builder.add_kpi_grid")
    @patch("src.design_renderer.pptx_engine.shape_builder.add_chart_image")
    def test_pptx_with_industry(
        self, mock_chart, mock_kpi, mock_data_with_industry: IMDocumentData,
    ):
        """industry 설정 시 PPTX 슬라이드 생성."""
        factory = MagicMock()
        slide_mock = MagicMock()
        factory.add_content_slide.return_value = slide_mock
        prs = MagicMock()

        renderer = get_renderer("industry_kpi")
        slides = renderer.render_pptx(
            factory, mock_data_with_industry, prs=prs, tokens=DEFAULT_TOKENS,
        )
        assert isinstance(slides, list)
        assert len(slides) >= 1
        factory.add_content_slide.assert_called_once()
        mock_kpi.assert_called_once()

    def test_pptx_without_industry(self, mock_data_no_industry: IMDocumentData):
        """industry 미설정 시 빈 리스트."""
        factory = MagicMock()
        prs = MagicMock()

        renderer = get_renderer("industry_kpi")
        slides = renderer.render_pptx(
            factory, mock_data_no_industry, prs=prs, tokens=DEFAULT_TOKENS,
        )
        assert slides == []


class TestIndustryOverviewRendererPptx:
    """IndustryOverviewRenderer PPTX 렌더링."""

    @patch("src.design_renderer.pptx_engine.shape_builder.add_financial_table")
    @patch("src.design_renderer.pptx_engine.shape_builder.add_chart_image")
    @patch("src.design_renderer.pptx_engine.shape_builder.add_bullet_list")
    @patch("src.design_renderer.pptx_engine.shape_builder.add_body_textbox")
    def test_pptx_with_industry(
        self, mock_body, mock_bullet, mock_chart, mock_table,
        mock_data_with_industry: IMDocumentData,
    ):
        """industry 설정 시 PPTX 슬라이드 생성."""
        factory = MagicMock()
        factory.add_content_slide.return_value = MagicMock()
        prs = MagicMock()

        renderer = get_renderer("industry_overview")
        slides = renderer.render_pptx(
            factory, mock_data_with_industry, prs=prs, tokens=DEFAULT_TOKENS,
        )
        assert isinstance(slides, list)
        assert len(slides) >= 1

    def test_pptx_without_industry(self, mock_data_no_industry: IMDocumentData):
        """industry 미설정 시 빈 리스트."""
        factory = MagicMock()
        prs = MagicMock()

        renderer = get_renderer("industry_overview")
        slides = renderer.render_pptx(
            factory, mock_data_no_industry, prs=prs, tokens=DEFAULT_TOKENS,
        )
        assert slides == []
