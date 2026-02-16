"""Stacked Bar 차트 (사업부별 매출 구성).

> 마지막 수정: 2026-02-10 13:45:13
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_stacked_bar_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Stacked Bar chart (사업부별 매출 구성).

    Args:
        data: {
            "categories": ["2021", "2022", "2023"],
            "series": [
                {"name": "IT서비스", "values": [50, 60, 70]},
                {"name": "SI", "values": [30, 35, 40]},
            ]
        }
        title: 차트 제목.
        config: 차트 설정.
        width: 오버라이드 너비 (px).
        height: 오버라이드 높이 (px).

    Returns:
        Plotly Figure.

    Raises:
        ChartDataError: 필수 데이터 키 누락 시.
    """
    cfg = config or DEFAULT_CHART_CONFIG
    theme = AMICThemeFactory(cfg)

    categories = data.get("categories", [])
    series = data.get("series", [])

    if not categories or not series:
        raise ChartDataError("stacked_bar", "categories와 series는 필수입니다.")

    colors = theme.get_color_sequence()

    fig = go.Figure()
    for i, s in enumerate(series):
        fig.add_trace(
            go.Bar(
                x=categories,
                y=s.get("values", []),
                name=s.get("name", f"Series {i}"),
                marker_color=colors[i % len(colors)],
            )
        )

    theme.apply_layout(fig, title=title, width=width, height=height)
    fig.update_layout(barmode="stack")
    return fig
