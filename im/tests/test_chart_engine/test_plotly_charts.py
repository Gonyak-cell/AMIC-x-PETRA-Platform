"""10종 Plotly 차트 + 디스패처 단위 테스트.

> 마지막 수정: 2026-02-11 10:00:00
"""

import math

import pytest

from src.chart_engine.exceptions import ChartDataError, UnsupportedChartTypeError
from src.chart_engine.plotly import (
    create_chart,
    create_cohort_heatmap_chart,
    create_combo_chart,
    create_donut_chart,
    create_funnel_chart,
    create_hbar_chart,
    create_line_chart,
    create_sensitivity_heatmap_chart,
    create_stacked_bar_chart,
    create_treemap_chart,
    create_waterfall_chart,
)

pytestmark = pytest.mark.requires_plotly


class TestWaterfallChart:
    """워터폴 차트."""

    def test_create(self, waterfall_data):
        """워터폴 차트 Figure 생성."""
        fig = create_waterfall_chart(waterfall_data, title="영업이익 워터폴")
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].type == "waterfall"

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="waterfall"):
            create_waterfall_chart({})


class TestComboChart:
    """콤보 차트 (바+라인)."""

    def test_create(self, combo_data):
        """콤보 차트 Figure 생성 (Bar + Scatter)."""
        fig = create_combo_chart(combo_data, title="매출 및 영업이익률")
        assert fig is not None
        assert len(fig.data) == 2
        assert fig.data[0].type == "bar"
        assert fig.data[1].type == "scatter"

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="combo"):
            create_combo_chart({})


class TestStackedBarChart:
    """누적 바 차트."""

    def test_create(self, stacked_bar_data):
        """누적 바 차트 생성 + barmode=stack."""
        fig = create_stacked_bar_chart(stacked_bar_data, title="사업부별 매출")
        assert fig is not None
        assert fig.layout.barmode == "stack"
        assert len(fig.data) == 3

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="stacked_bar"):
            create_stacked_bar_chart({})


class TestDonutChart:
    """도넛 차트."""

    def test_create(self, donut_data):
        """도넛 차트 생성 (hole=0.4)."""
        fig = create_donut_chart(donut_data, title="시장 점유율")
        assert fig is not None
        assert fig.data[0].type == "pie"
        assert fig.data[0].hole == 0.4

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="donut"):
            create_donut_chart({})


class TestLineChart:
    """라인 차트."""

    def test_create(self, line_data):
        """라인 차트 생성."""
        fig = create_line_chart(line_data, title="매출 추이")
        assert fig is not None
        assert fig.data[0].type == "scatter"
        assert fig.data[0].mode == "lines+markers"

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="line"):
            create_line_chart({})


class TestHbarChart:
    """수평 바 차트."""

    def test_create(self, hbar_data):
        """수평 바 차트 생성."""
        fig = create_hbar_chart(hbar_data, title="경쟁사 비교")
        assert fig is not None
        assert fig.data[0].orientation == "h"

    def test_highlight_color(self, hbar_data):
        """하이라이트 항목의 색상."""
        from src.chart_engine.config import DEFAULT_CHART_CONFIG

        fig = create_hbar_chart(hbar_data)
        c = DEFAULT_CHART_CONFIG.colors
        # 자사(index 2)가 accent 색상
        colors = list(fig.data[0].marker.color)
        assert colors[2] == c.accent  # "자사"
        assert colors[0] == c.primary  # "경쟁사A"

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="hbar"):
            create_hbar_chart({})


# ---------------------------------------------------------------------------
# 신규 차트 4종
# ---------------------------------------------------------------------------


class TestFunnelChart:
    """퍼널 차트."""

    def test_create(self, funnel_data):
        """퍼널 차트 Figure 생성."""
        fig = create_funnel_chart(funnel_data, title="시장 규모 퍼널")
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].type == "funnel"

    def test_custom_colors(self, funnel_data):
        """사용자 정의 색상 적용."""
        funnel_data["colors"] = ["#FF0000", "#00FF00", "#0000FF"]
        fig = create_funnel_chart(funnel_data)
        colors = list(fig.data[0].marker.color)
        assert colors == ["#FF0000", "#00FF00", "#0000FF"]

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="funnel"):
            create_funnel_chart({})


class TestSensitivityHeatmapChart:
    """민감도 히트맵 차트."""

    def test_create(self, sensitivity_heatmap_data):
        """민감도 히트맵 Figure 생성."""
        fig = create_sensitivity_heatmap_chart(
            sensitivity_heatmap_data, title="IRR 민감도"
        )
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].type == "heatmap"

    def test_text_annotations(self, sensitivity_heatmap_data):
        """셀 텍스트 어노테이션 존재."""
        fig = create_sensitivity_heatmap_chart(sensitivity_heatmap_data)
        assert fig.data[0].text is not None
        assert fig.data[0].texttemplate == "%{text}"

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="heatmap"):
            create_sensitivity_heatmap_chart({})


class TestCohortHeatmapChart:
    """코호트 히트맵 차트."""

    def test_create(self, cohort_heatmap_data):
        """코호트 히트맵 Figure 생성."""
        fig = create_cohort_heatmap_chart(
            cohort_heatmap_data, title="리텐션 코호트"
        )
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].type == "heatmap"

    def test_none_values_handled(self, cohort_heatmap_data):
        """None 값이 NaN으로 변환."""
        fig = create_cohort_heatmap_chart(cohort_heatmap_data)
        z = fig.data[0].z
        # 마지막 행의 마지막 두 값이 NaN
        assert math.isnan(z[2][2])
        assert math.isnan(z[2][3])

    def test_fixed_scale(self, cohort_heatmap_data):
        """zmin=0, zmax=100 고정 스케일."""
        fig = create_cohort_heatmap_chart(cohort_heatmap_data)
        assert fig.data[0].zmin == 0
        assert fig.data[0].zmax == 100

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="cohort_heatmap"):
            create_cohort_heatmap_chart({})


class TestTreemapChart:
    """트리맵 차트."""

    def test_create(self, treemap_data):
        """트리맵 Figure 생성."""
        fig = create_treemap_chart(treemap_data, title="매출 구조")
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].type == "treemap"

    def test_labels_and_parents(self, treemap_data):
        """labels와 parents 올바르게 전달."""
        fig = create_treemap_chart(treemap_data)
        assert len(fig.data[0].labels) == 6
        assert fig.data[0].parents[0] == ""  # 루트

    def test_empty_data_raises(self):
        """빈 데이터 시 ChartDataError."""
        with pytest.raises(ChartDataError, match="treemap"):
            create_treemap_chart({})


# ---------------------------------------------------------------------------
# 디스패처
# ---------------------------------------------------------------------------


class TestChartDispatcher:
    """범용 디스패처."""

    def test_dispatch_valid_type(self, combo_data):
        """유효한 차트 유형 디스패치."""
        fig = create_chart("combo", combo_data, title="테스트")
        assert fig is not None

    def test_dispatch_invalid_type(self):
        """유효하지 않은 차트 유형 시 UnsupportedChartTypeError."""
        with pytest.raises(UnsupportedChartTypeError, match="unknown"):
            create_chart("unknown", {})

    def test_chart_data_validation(self):
        """디스패처 경유 데이터 검증."""
        with pytest.raises(ChartDataError):
            create_chart("waterfall", {})

    @pytest.mark.parametrize(
        "chart_type,fixture_name",
        [
            ("funnel", "funnel_data"),
            ("heatmap", "sensitivity_heatmap_data"),
            ("cohort_heatmap", "cohort_heatmap_data"),
            ("treemap", "treemap_data"),
        ],
    )
    def test_dispatch_new_types(self, chart_type, fixture_name, request):
        """신규 차트 유형 디스패치."""
        data = request.getfixturevalue(fixture_name)
        fig = create_chart(chart_type, data, title="테스트")
        assert fig is not None
