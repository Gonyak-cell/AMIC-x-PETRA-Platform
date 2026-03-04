"""Sensitivity Heatmap 차트 (IRR/MOIC 민감도 분석).

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import DEFAULT_CHART_CONFIG, ChartConfig
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_sensitivity_heatmap_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """민감도 히트맵 (IRR/MOIC 민감도 테이블).

    Args:
        data: {
            "x_labels": ["8x", "9x", "10x", "11x", "12x"],
            "y_labels": ["6x", "7x", "8x", "9x", "10x"],
            "z_values": [[15.2, 18.1, ...], ...],
            "x_title": "Exit Multiple",
            "y_title": "Entry Multiple",
            "z_format": ".1f",        # 선택 (기본 ".1f")
            "z_suffix": "%",          # 선택 (기본 "")
            "colorscale": "RdYlGn",   # 선택 (기본 "RdYlGn")
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

    x_labels = data.get("x_labels", [])
    y_labels = data.get("y_labels", [])
    z_values = data.get("z_values", [])

    if not x_labels or not y_labels or not z_values:
        raise ChartDataError("heatmap", "x_labels, y_labels, z_values는 필수입니다.")

    x_title = data.get("x_title", "")
    y_title = data.get("y_title", "")
    z_format = data.get("z_format", ".1f")
    z_suffix = data.get("z_suffix", "")
    colorscale = data.get("colorscale", "RdYlGn")

    text = [[f"{val:{z_format}}{z_suffix}" for val in row] for row in z_values]

    fig = go.Figure(
        go.Heatmap(
            x=x_labels,
            y=y_labels,
            z=z_values,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=10, family=cfg.font),
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=dict(text=z_suffix, font=dict(size=9)),
                tickfont=dict(size=8),
                len=0.8,
            ),
            hovertemplate=(
                f"{x_title}: %{{x}}<br>"
                f"{y_title}: %{{y}}<br>"
                f"값: %{{text}}<extra></extra>"
            ),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)

    if x_title:
        fig.update_xaxes(title_text=x_title, side="bottom")
    if y_title:
        fig.update_yaxes(title_text=y_title)

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")

    return fig
