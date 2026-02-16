"""Treemap 차트 (매출 세그먼트, 비용 구조 분해).

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import DEFAULT_CHART_CONFIG, ChartConfig
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_treemap_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """트리맵 차트 (매출 세그먼트, 비용 구조 분해).

    Args:
        data: {
            "labels": ["전체", "IT서비스", "SI", "컨설팅", "클라우드", "보안"],
            "parents": ["", "전체", "전체", "전체", "IT서비스", "IT서비스"],
            "values": [0, 60000, 30000, 10000, 40000, 20000],
            "colors": [...],  # 선택
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

    labels = data.get("labels", [])
    parents = data.get("parents", [])
    values = data.get("values", [])

    if not labels or not parents:
        raise ChartDataError("treemap", "labels와 parents는 필수입니다.")

    colors = data.get("colors")
    if colors:
        marker_colors = colors[: len(labels)]
    else:
        seq = theme.get_color_sequence()
        marker_colors = []
        color_idx = 0
        for parent in parents:
            if parent == "":
                marker_colors.append("rgba(0,0,0,0)")
            else:
                marker_colors.append(seq[color_idx % len(seq)])
                color_idx += 1

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values if values else None,
            textinfo="label+value+percent parent",
            textfont=dict(family=cfg.font, size=11),
            marker=dict(colors=marker_colors),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "값: %{value:,.0f}<br>"
                "비중: %{percentParent:.1%}<extra></extra>"
            ),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)
    fig.update_layout(
        margin=dict(l=10, r=10, t=50 if title else 20, b=10),
    )
    return fig
