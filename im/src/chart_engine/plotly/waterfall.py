"""Waterfall 차트 (영업이익 Bridge).

> 마지막 수정: 2026-02-10 13:45:13
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_waterfall_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Waterfall chart (영업이익 Bridge).

    Args:
        data: {
            "categories": ["매출", "매출원가", "판관비", "영업이익"],
            "values": [150000, -80000, -30000, 40000],
            "measure": ["absolute", "relative", "relative", "total"]
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

    categories = data.get("categories", [])
    values = data.get("values", [])

    if not categories or not values:
        raise ChartDataError("waterfall", "categories와 values는 필수입니다.")

    measures = data.get("measure", ["relative"] * len(values))

    fig = go.Figure(
        go.Waterfall(
            name="",
            orientation="v",
            measure=measures,
            x=categories,
            y=values,
            connector=dict(line=dict(color=c.gray_medium, width=1)),
            increasing=dict(marker=dict(color=c.accent)),
            decreasing=dict(marker=dict(color=c.negative)),
            totals=dict(marker=dict(color=c.primary)),
            textposition="outside",
            texttemplate="%{y:,.0f}",
            textfont=dict(size=9),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)
    fig.update_layout(showlegend=False)
    return fig
