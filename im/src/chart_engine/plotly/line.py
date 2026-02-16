"""Multi-series Line 차트 (KPI 추이).

> 마지막 수정: 2026-02-10 13:45:13
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_line_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Multi-series Line chart (KPI 추이).

    Args:
        data: {
            "x": ["2020", "2021", "2022", "2023", "2024"],
            "series": [
                {"name": "매출", "values": [100, 120, 140, 160, 180]},
                {"name": "영업이익", "values": [10, 15, 20, 25, 30]},
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

    x = data.get("x", [])
    series = data.get("series", [])

    if not x or not series:
        raise ChartDataError("line", "x와 series는 필수입니다.")

    colors = theme.get_color_sequence()

    fig = go.Figure()
    for i, s in enumerate(series):
        fig.add_trace(
            go.Scatter(
                x=x,
                y=s.get("values", []),
                name=s.get("name", f"Series {i}"),
                mode="lines+markers",
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=6),
            )
        )

    theme.apply_layout(fig, title=title, width=width, height=height)
    return fig
