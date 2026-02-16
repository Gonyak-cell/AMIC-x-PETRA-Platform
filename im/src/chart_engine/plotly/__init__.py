"""Plotly 차트 서브패키지 — 10종 차트 + AMIC 테마 + 범용 디스패처.

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from typing import Any, Callable

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig
from src.chart_engine.exceptions import UnsupportedChartTypeError
from src.chart_engine.plotly.cohort_heatmap import create_cohort_heatmap_chart
from src.chart_engine.plotly.combo import create_combo_chart
from src.chart_engine.plotly.donut import create_donut_chart
from src.chart_engine.plotly.funnel import create_funnel_chart
from src.chart_engine.plotly.hbar import create_hbar_chart
from src.chart_engine.plotly.line import create_line_chart
from src.chart_engine.plotly.sensitivity_heatmap import create_sensitivity_heatmap_chart
from src.chart_engine.plotly.stacked_bar import create_stacked_bar_chart
from src.chart_engine.plotly.themes import AMICThemeFactory
from src.chart_engine.plotly.treemap import create_treemap_chart
from src.chart_engine.plotly.waterfall import create_waterfall_chart

CHART_DISPATCH: dict[str, Callable[..., go.Figure]] = {
    "waterfall": create_waterfall_chart,
    "combo": create_combo_chart,
    "stacked_bar": create_stacked_bar_chart,
    "donut": create_donut_chart,
    "line": create_line_chart,
    "hbar": create_hbar_chart,
    "funnel": create_funnel_chart,
    "heatmap": create_sensitivity_heatmap_chart,
    "cohort_heatmap": create_cohort_heatmap_chart,
    "treemap": create_treemap_chart,
}


def create_chart(
    chart_type: str,
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """chart_type에 따라 적절한 차트 생성 함수 디스패치.

    Args:
        chart_type: 차트 유형 ("waterfall", "combo", "stacked_bar", "donut", "line",
            "hbar", "funnel", "heatmap", "cohort_heatmap", "treemap").
        data: 차트 데이터 dict.
        title: 차트 제목.
        config: 차트 설정. None이면 기본값 사용.
        width: 오버라이드 너비 (px).
        height: 오버라이드 높이 (px).

    Returns:
        Plotly Figure.

    Raises:
        UnsupportedChartTypeError: 지원하지 않는 chart_type.
    """
    creator = CHART_DISPATCH.get(chart_type)
    if creator is None:
        raise UnsupportedChartTypeError(chart_type, list(CHART_DISPATCH.keys()))

    return creator(
        data,
        title=title,
        config=config,
        width=width,
        height=height,
    )


__all__ = [
    "AMICThemeFactory",
    "CHART_DISPATCH",
    "create_chart",
    "create_cohort_heatmap_chart",
    "create_combo_chart",
    "create_donut_chart",
    "create_funnel_chart",
    "create_hbar_chart",
    "create_line_chart",
    "create_sensitivity_heatmap_chart",
    "create_stacked_bar_chart",
    "create_treemap_chart",
    "create_waterfall_chart",
]
