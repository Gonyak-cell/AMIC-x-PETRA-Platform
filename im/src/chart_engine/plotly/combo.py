"""Dual-Axis Combo 차트 (막대 + 꺾은선).

> 마지막 수정: 2026-02-10 13:45:13
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_combo_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Dual-Axis Combo chart (막대 + 꺾은선).

    Args:
        data: {
            "years": ["2021", "2022", "2023", "2024"],
            "bar_values": [100, 120, 140, 160],
            "bar_name": "매출",
            "line_values": [0.10, 0.12, 0.15, 0.18],
            "line_name": "영업이익률",
        }
        title: 차트 제목.
        config: 차트 설정.
        width: 오버라이드 너비 (px).
        height: 오버라이드 높이 (px).

    Returns:
        Plotly Figure with secondary y-axis.

    Raises:
        ChartDataError: 필수 데이터 키 누락 시.
    """
    cfg = config or DEFAULT_CHART_CONFIG
    theme = AMICThemeFactory(cfg)
    c = cfg.colors

    years = data.get("years", [])
    bar_values = data.get("bar_values", [])
    bar_name = data.get("bar_name", "Bar")
    line_values = data.get("line_values", [])
    line_name = data.get("line_name", "Line")

    if not years or not bar_values:
        raise ChartDataError("combo", "years와 bar_values는 필수입니다.")

    # line_values None 안전 처리
    if line_values:
        line_values = [float(v) if v is not None else 0.0 for v in line_values]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 막대 (좌축)
    fig.add_trace(
        go.Bar(
            x=years,
            y=bar_values,
            name=bar_name,
            marker_color=c.primary,
            texttemplate="%{y:,.0f}",
            textposition="outside",
            textfont=dict(size=8),
        ),
        secondary_y=False,
    )

    # 꺾은선 (우축)
    fig.add_trace(
        go.Scatter(
            x=years,
            y=line_values,
            name=line_name,
            mode="lines+markers+text",
            line=dict(color=c.accent, width=2.5),
            marker=dict(size=7, color=c.accent),
            text=[f"{v * 100:.1f}%" for v in line_values],
            textposition="top center",
            textfont=dict(size=8),
        ),
        secondary_y=True,
    )

    theme.apply_layout(fig, title=title, width=width, height=height)

    fig.update_yaxes(title_text=bar_name, secondary_y=False)
    fig.update_yaxes(
        title_text=line_name,
        secondary_y=True,
        tickformat=".0%",
        showgrid=False,
    )

    return fig
