"""Funnel 차트 (TAM/SAM/SOM, 세일즈 파이프라인).

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import DEFAULT_CHART_CONFIG, ChartConfig
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_funnel_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """퍼널 차트 생성. TAM/SAM/SOM 또는 파이프라인 시각화.

    Args:
        data: {
            "stages": ["TAM", "SAM", "SOM"],
            "values": [50000, 12000, 3000],
            "colors": ["#0F3A32", "#26C260", "#4CAF50"],  # 선택
        }
        title: 차트 제목.
        config: 차트 설정. None이면 DEFAULT_CHART_CONFIG 사용.
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

    stages = data.get("stages", [])
    values = data.get("values", [])

    if not stages or not values:
        raise ChartDataError("funnel", "stages와 values는 필수입니다.")

    colors = data.get("colors") or theme.get_color_sequence()

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            textposition="inside",
            textfont=dict(size=10, family=cfg.font),
            marker=dict(
                color=colors[: len(stages)],
                line=dict(width=1, color=c.gray_border),
            ),
            connector=dict(line=dict(color=c.gray_medium, width=1)),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)
    fig.update_layout(showlegend=False)
    return fig
