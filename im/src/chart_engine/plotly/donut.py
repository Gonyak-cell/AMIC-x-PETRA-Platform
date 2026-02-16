"""Donut 차트 (시장 점유율).

> 마지막 수정: 2026-02-10 13:45:13
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_donut_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Donut chart (시장 점유율).

    Args:
        data: {
            "labels": ["당사", "경쟁사A", "경쟁사B", "기타"],
            "values": [30, 25, 20, 25],
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

    labels = data.get("labels", [])
    values = data.get("values", [])

    if not labels or not values:
        raise ChartDataError("donut", "labels와 values는 필수입니다.")

    colors = theme.get_color_sequence()

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=colors[: len(labels)]),
            textinfo="label+percent",
            textposition="outside",
            textfont=dict(size=9),
            outsidetextfont=dict(family=cfg.font),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)
    return fig
