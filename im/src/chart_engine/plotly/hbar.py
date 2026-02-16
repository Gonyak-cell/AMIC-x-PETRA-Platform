"""Horizontal Bar 차트 (경쟁사 비교).

> 마지막 수정: 2026-02-10 13:45:13
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_hbar_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Horizontal Bar chart (경쟁사 비교).

    Args:
        data: {
            "categories": ["경쟁사A", "경쟁사B", "당사", "경쟁사C"],
            "values": [120, 100, 95, 80],
            "highlight": "당사",  # 강조할 항목 (optional)
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
    c = cfg.colors

    categories = data.get("categories", [])
    values = data.get("values", [])
    highlight = data.get("highlight", "")

    if not categories or not values:
        raise ChartDataError("hbar", "categories와 values는 필수입니다.")

    # 하이라이트 색상
    bar_colors = [c.accent if cat == highlight else c.primary for cat in categories]

    fig = go.Figure(
        go.Bar(
            y=categories,
            x=values,
            orientation="h",
            marker_color=bar_colors,
            texttemplate="%{x:,.0f}",
            textposition="outside",
            textfont=dict(size=9),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(autorange="reversed")
    return fig
