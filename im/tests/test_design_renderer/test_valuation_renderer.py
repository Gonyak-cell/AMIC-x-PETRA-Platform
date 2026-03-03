"""밸류에이션 섹션 렌더러 테스트 (Phase D1).

> 마지막 수정: 2026-02-11 22:00:00
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.design_renderer.im_document import (
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
    """HTML 렌더링 테스트 — render_html은 PPTX 전용 전환으로 제거됨."""

    def test_render_html_raises_not_implemented(self) -> None:
        """render_html()은 NotImplementedError를 발생시킨다."""
        data = _make_data_with_valuation()
        renderer = ValuationRenderer()
        with pytest.raises(NotImplementedError, match="PDF output removed"):
            renderer.render_html(data)


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
