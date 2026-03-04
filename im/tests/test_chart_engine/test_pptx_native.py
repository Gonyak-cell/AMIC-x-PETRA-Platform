"""네이티브 PPTX 차트 빌더 테스트.

> 마지막 수정: 2026-02-27 10:28:00

4종 네이티브 빌더(stacked_bar, donut, line, hbar)의
차트 생성·데이터 검증·스타일 적용·하이브리드 디스패치를 검증한다.
"""

from __future__ import annotations

from typing import Any

import pytest
from pptx import Presentation
from pptx.enum.chart import XL_CHART_TYPE

from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.pptx_native import (
    NATIVE_CHART_TYPES,
    get_native_builder,
    is_native_supported,
)
from src.chart_engine.pptx_native.donut import DonutBuilder
from src.chart_engine.pptx_native.hbar import HBarBuilder
from src.chart_engine.pptx_native.line_chart import LineChartBuilder
from src.chart_engine.pptx_native.stacked_bar import StackedBarBuilder


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_slide() -> Any:
    """테스트용 빈 PPTX 슬라이드 생성."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # Blank layout
    return slide, prs


# ---------------------------------------------------------------------------
# 레지스트리 / 디스패치 테스트
# ---------------------------------------------------------------------------


class TestNativeRegistry:
    """네이티브 빌더 레지스트리 테스트."""

    def test_supported_types(self):
        assert NATIVE_CHART_TYPES == frozenset({"stacked_bar", "donut", "line", "hbar"})

    def test_is_native_supported_true(self):
        for ct in ("stacked_bar", "donut", "line", "hbar"):
            assert is_native_supported(ct) is True

    def test_is_native_supported_false(self):
        for ct in ("waterfall", "combo", "heatmap", "funnel", "treemap", ""):
            assert is_native_supported(ct) is False

    def test_get_native_builder(self):
        assert isinstance(get_native_builder("stacked_bar"), StackedBarBuilder)
        assert isinstance(get_native_builder("donut"), DonutBuilder)
        assert isinstance(get_native_builder("line"), LineChartBuilder)
        assert isinstance(get_native_builder("hbar"), HBarBuilder)

    def test_get_native_builder_unknown(self):
        assert get_native_builder("waterfall") is None
        assert get_native_builder("") is None


# ---------------------------------------------------------------------------
# Stacked Bar 빌더 테스트
# ---------------------------------------------------------------------------


class TestStackedBarBuilder:
    """COLUMN_STACKED 네이티브 차트 빌더 테스트."""

    def test_build_basic(self, stacked_bar_data: dict[str, Any]):
        slide, prs = _make_slide()
        builder = StackedBarBuilder()
        shape = builder.build(slide, stacked_bar_data, title="사업부별 매출")

        assert shape is not None
        chart = shape.chart
        assert chart.chart_type == XL_CHART_TYPE.COLUMN_STACKED

    def test_series_count(self, stacked_bar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = StackedBarBuilder().build(slide, stacked_bar_data)
        chart = shape.chart
        assert len(chart.plots[0].series) == 3  # IT서비스, SI, 기타

    def test_categories(self, stacked_bar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = StackedBarBuilder().build(slide, stacked_bar_data)
        chart = shape.chart
        cats = [str(c) for c in chart.plots[0].categories]
        assert cats == ["2022", "2023", "2024"]

    def test_title_set(self, stacked_bar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = StackedBarBuilder().build(slide, stacked_bar_data, title="테스트 제목")
        assert shape.chart.chart_title.text_frame.text == "테스트 제목"

    def test_empty_data_raises(self):
        slide, _ = _make_slide()
        with pytest.raises(ChartDataError):
            StackedBarBuilder().build(slide, {"categories": [], "series": []})

    def test_gap_width(self, stacked_bar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = StackedBarBuilder().build(slide, stacked_bar_data)
        assert shape.chart.plots[0].gap_width == 80


# ---------------------------------------------------------------------------
# Donut 빌더 테스트
# ---------------------------------------------------------------------------


class TestDonutBuilder:
    """DOUGHNUT 네이티브 차트 빌더 테스트."""

    def test_build_basic(self, donut_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = DonutBuilder().build(slide, donut_data, title="시장 점유율")
        chart = shape.chart
        assert chart.chart_type == XL_CHART_TYPE.DOUGHNUT

    def test_categories(self, donut_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = DonutBuilder().build(slide, donut_data)
        cats = [str(c) for c in shape.chart.plots[0].categories]
        assert cats == ["IT서비스", "SI", "기타"]

    def test_data_labels_enabled(self, donut_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = DonutBuilder().build(slide, donut_data)
        assert shape.chart.plots[0].has_data_labels is True

    def test_empty_data_raises(self):
        slide, _ = _make_slide()
        with pytest.raises(ChartDataError):
            DonutBuilder().build(slide, {"labels": [], "values": []})


# ---------------------------------------------------------------------------
# Line 빌더 테스트
# ---------------------------------------------------------------------------


class TestLineChartBuilder:
    """LINE_MARKERS 네이티브 차트 빌더 테스트."""

    def test_build_basic(self, line_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = LineChartBuilder().build(slide, line_data, title="KPI 추이")
        chart = shape.chart
        assert chart.chart_type == XL_CHART_TYPE.LINE_MARKERS

    def test_series_count(self, line_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = LineChartBuilder().build(slide, line_data)
        assert len(shape.chart.plots[0].series) == 1  # 매출

    def test_multi_series(self):
        slide, _ = _make_slide()
        data = {
            "x": ["Q1", "Q2", "Q3"],
            "series": [
                {"name": "매출", "values": [100, 120, 140]},
                {"name": "이익", "values": [10, 15, 20]},
            ],
        }
        shape = LineChartBuilder().build(slide, data)
        assert len(shape.chart.plots[0].series) == 2

    def test_categories(self, line_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = LineChartBuilder().build(slide, line_data)
        cats = [str(c) for c in shape.chart.plots[0].categories]
        assert cats == ["2022", "2023", "2024"]

    def test_empty_data_raises(self):
        slide, _ = _make_slide()
        with pytest.raises(ChartDataError):
            LineChartBuilder().build(slide, {"x": [], "series": []})


# ---------------------------------------------------------------------------
# HBar 빌더 테스트
# ---------------------------------------------------------------------------


class TestHBarBuilder:
    """BAR_CLUSTERED (horizontal) 네이티브 차트 빌더 테스트."""

    def test_build_basic(self, hbar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = HBarBuilder().build(slide, hbar_data, title="경쟁사 비교")
        chart = shape.chart
        assert chart.chart_type == XL_CHART_TYPE.BAR_CLUSTERED

    def test_no_legend(self, hbar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = HBarBuilder().build(slide, hbar_data)
        assert shape.chart.has_legend is False

    def test_data_labels(self, hbar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = HBarBuilder().build(slide, hbar_data)
        assert shape.chart.plots[0].has_data_labels is True

    def test_empty_data_raises(self):
        slide, _ = _make_slide()
        with pytest.raises(ChartDataError):
            HBarBuilder().build(slide, {"categories": [], "values": []})


# ---------------------------------------------------------------------------
# 스타일링 테스트
# ---------------------------------------------------------------------------


class TestStyling:
    """AMIC 디자인 토큰 적용 테스트."""

    def test_series_colors_applied(self, stacked_bar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = StackedBarBuilder().build(slide, stacked_bar_data)
        chart = shape.chart
        series0 = chart.plots[0].series[0]
        # fill이 설정되어 있어야 함
        assert series0.format.fill.fore_color is not None

    def test_axis_gridlines(self, line_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = LineChartBuilder().build(slide, line_data)
        chart = shape.chart
        assert chart.value_axis.has_major_gridlines is True

    def test_legend_enabled_for_multi_series(self, stacked_bar_data: dict[str, Any]):
        slide, _ = _make_slide()
        shape = StackedBarBuilder().build(slide, stacked_bar_data)
        assert shape.chart.has_legend is True


# ---------------------------------------------------------------------------
# PPTX 저장·재로드 테스트
# ---------------------------------------------------------------------------


class TestPptxRoundTrip:
    """PPTX 파일 저장 후 다시 열어 데이터 무결성 확인."""

    def test_save_and_reload(self, stacked_bar_data: dict[str, Any], tmp_path):
        slide, prs = _make_slide()
        StackedBarBuilder().build(slide, stacked_bar_data, title="Round Trip Test")

        path = tmp_path / "test_native_chart.pptx"
        prs.save(str(path))

        # 파일이 존재하고 0바이트 아닌지
        assert path.exists()
        assert path.stat().st_size > 0

        # 다시 열기
        prs2 = Presentation(str(path))
        assert len(prs2.slides) == 1
        slide2 = prs2.slides[0]

        # 차트 shape이 존재하는지
        chart_shapes = [s for s in slide2.shapes if s.has_chart]
        assert len(chart_shapes) == 1
        assert chart_shapes[0].chart.chart_type == XL_CHART_TYPE.COLUMN_STACKED

    def test_all_builders_save(
        self,
        stacked_bar_data,
        donut_data,
        line_data,
        hbar_data,
        tmp_path,
    ):
        """4종 빌더 모두 PPTX에 저장 가능."""
        prs = Presentation()
        builders_data = [
            (StackedBarBuilder(), stacked_bar_data, "Stacked"),
            (DonutBuilder(), donut_data, "Donut"),
            (LineChartBuilder(), line_data, "Line"),
            (HBarBuilder(), hbar_data, "HBar"),
        ]

        for builder, data, title in builders_data:
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            builder.build(slide, data, title=title)

        path = tmp_path / "test_all_native.pptx"
        prs.save(str(path))

        assert path.stat().st_size > 0

        prs2 = Presentation(str(path))
        assert len(prs2.slides) == 4

        chart_types = []
        for s in prs2.slides:
            for shape in s.shapes:
                if shape.has_chart:
                    chart_types.append(shape.chart.chart_type)

        assert XL_CHART_TYPE.COLUMN_STACKED in chart_types
        assert XL_CHART_TYPE.DOUGHNUT in chart_types
        assert XL_CHART_TYPE.LINE_MARKERS in chart_types
        assert XL_CHART_TYPE.BAR_CLUSTERED in chart_types
