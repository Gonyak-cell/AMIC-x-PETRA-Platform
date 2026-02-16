"""밸류에이션 섹션 렌더러 테스트 (Phase D1).

> 마지막 수정: 2026-02-11 22:00:00
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.design_renderer.im_document import (
    ChartData,
    IMDocumentData,
    IMStyle,
    ValuationData,
)
from src.design_renderer.section_renderers import RENDERER_REGISTRY
from src.design_renderer.section_renderers.valuation import ValuationRenderer


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


def _make_valuation_data() -> ValuationData:
    """테스트용 밸류에이션 데이터."""
    return ValuationData(
        ev_ebitda={"2023": 10.0, "2024": 8.5},
        pe_ratio={"2023": 15.0},
        ev_revenue={"2023": 2.0},
        irr_scenarios={
            "base": {
                "entry_multiple": 8.0,
                "exit_multiple": 10.0,
                "holding_period": 5,
                "irr": 18.5,
            },
            "upside": {
                "entry_multiple": 7.0,
                "exit_multiple": 12.0,
                "holding_period": 4,
                "irr": 28.3,
            },
        },
        moic_scenarios={"base": 2.5, "upside": 3.5},
        exit_analysis={
            "8.0x": {
                "exit_multiple": 8.0,
                "exit_ev": 400000,
                "exit_equity": 300000,
                "moic": 3.0,
                "irr": 24.5,
            },
            "10.0x": {
                "exit_multiple": 10.0,
                "exit_ev": 500000,
                "exit_equity": 400000,
                "moic": 4.0,
                "irr": 32.0,
            },
        },
    )


def _make_data_with_valuation() -> IMDocumentData:
    """밸류에이션 데이터 포함 IMDocumentData."""
    return IMDocumentData(
        im_style=IMStyle.CUSTOM,
        sections=["valuation"],
        valuation_data=_make_valuation_data(),
        narratives={"valuation": "EV/EBITDA 10.0x 기준으로 산정하였습니다."},
    )


def _make_minimal_data() -> IMDocumentData:
    """최소 데이터 (valuation_data 없음)."""
    return IMDocumentData(
        im_style=IMStyle.CUSTOM,
        sections=["valuation"],
    )


# ---------------------------------------------------------------------------
# 레지스트리 테스트
# ---------------------------------------------------------------------------


class TestValuationRendererRegistry:
    """ValuationRenderer 레지스트리 등록."""

    def test_registered(self) -> None:
        assert "valuation" in RENDERER_REGISTRY
        assert RENDERER_REGISTRY["valuation"] is ValuationRenderer


# ---------------------------------------------------------------------------
# HTML 렌더링
# ---------------------------------------------------------------------------


class TestValuationRendererHtml:
    """HTML 렌더링 테스트."""

    def test_kpi_slide_rendered(self) -> None:
        """KPI + narrative 슬라이드는 항상 생성된다."""
        data = _make_data_with_valuation()
        renderer = ValuationRenderer()
        slides = renderer.render_html(data)
        assert len(slides) >= 1
        assert "밸류에이션 요약" in slides[0]
        assert "EV/EBITDA" in slides[0]
        assert "10.0x" in slides[0]

    def test_scenario_table_rendered(self) -> None:
        """IRR/MOIC 시나리오 테이블이 생성된다."""
        data = _make_data_with_valuation()
        renderer = ValuationRenderer()
        slides = renderer.render_html(data)
        # 최소 2개 슬라이드: KPI + scenario table
        assert len(slides) >= 2
        assert "시나리오 분석" in slides[1]

    def test_exit_table_rendered(self) -> None:
        """Exit 전략 비교 테이블이 생성된다."""
        data = _make_data_with_valuation()
        renderer = ValuationRenderer()
        slides = renderer.render_html(data)
        # Exit table 존재 확인
        exit_slides = [s for s in slides if "Exit 전략" in s]
        assert len(exit_slides) == 1

    def test_minimal_data_single_slide(self) -> None:
        """valuation_data가 없으면 KPI 슬라이드 1개만 생성."""
        data = _make_minimal_data()
        renderer = ValuationRenderer()
        slides = renderer.render_html(data)
        assert len(slides) == 1
        assert "밸류에이션 요약" in slides[0]

    def test_chart_slides_rendered(self) -> None:
        """차트가 있으면 차트 슬라이드가 추가된다."""
        data = _make_data_with_valuation()
        data.charts = {
            "valuation": [
                ChartData(
                    chart_type="heatmap",
                    title="IRR 민감도",
                    data={"image_path": "/tmp/heatmap.png"},
                ),
            ],
        }
        renderer = ValuationRenderer()
        slides = renderer.render_html(data)
        chart_slides = [s for s in slides if "IRR 민감도" in s]
        assert len(chart_slides) == 1


# ---------------------------------------------------------------------------
# PPTX 렌더링
# ---------------------------------------------------------------------------


_SHAPE_BUILDER = "src.design_renderer.pptx_engine.shape_builder"


class TestValuationRendererPptx:
    """PPTX 렌더링 테스트."""

    def _make_factory(self) -> MagicMock:
        factory = MagicMock()
        factory.add_content_slide.return_value = MagicMock()
        return factory

    @patch(f"{_SHAPE_BUILDER}.add_kpi_grid", return_value=[])
    @patch(f"{_SHAPE_BUILDER}.add_body_textbox")
    @patch(f"{_SHAPE_BUILDER}.add_financial_table")
    @patch(f"{_SHAPE_BUILDER}.add_chart_image")
    def test_pptx_all_slides(self, m_chart, m_table, m_body, m_kpi) -> None:
        """전체 데이터 → 최소 3개 슬라이드 (KPI + scenarios + exit)."""
        data = _make_data_with_valuation()
        renderer = ValuationRenderer()
        factory = self._make_factory()
        slides = renderer.render_pptx(factory, data, prs=MagicMock())
        # KPI(1) + scenario(1) + exit(1) = 최소 3
        assert len(slides) >= 3
        m_kpi.assert_called_once()

    @patch(f"{_SHAPE_BUILDER}.add_kpi_grid", return_value=[])
    @patch(f"{_SHAPE_BUILDER}.add_body_textbox")
    @patch(f"{_SHAPE_BUILDER}.add_financial_table")
    def test_pptx_minimal_single_slide(self, m_table, m_body, m_kpi) -> None:
        """valuation_data 없으면 1개 슬라이드."""
        data = _make_minimal_data()
        renderer = ValuationRenderer()
        factory = self._make_factory()
        slides = renderer.render_pptx(factory, data, prs=MagicMock())
        assert len(slides) == 1

    @patch(f"{_SHAPE_BUILDER}.add_kpi_grid", return_value=[])
    @patch(f"{_SHAPE_BUILDER}.add_body_textbox")
    @patch(f"{_SHAPE_BUILDER}.add_financial_table")
    @patch(f"{_SHAPE_BUILDER}.add_chart_image")
    def test_pptx_factory_called(self, m_chart, m_table, m_body, m_kpi) -> None:
        """factory.add_content_slide가 호출된다."""
        data = _make_data_with_valuation()
        renderer = ValuationRenderer()
        factory = self._make_factory()
        renderer.render_pptx(factory, data, prs=MagicMock())
        assert factory.add_content_slide.call_count >= 1
