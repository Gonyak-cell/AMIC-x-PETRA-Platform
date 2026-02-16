"""Cohort Heatmap 차트 (SaaS 리텐션 코호트 분석).

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import DEFAULT_CHART_CONFIG, ChartConfig
from src.chart_engine.exceptions import ChartDataError
from src.chart_engine.plotly.themes import AMICThemeFactory


def create_cohort_heatmap_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """코호트 히트맵 (SaaS 리텐션 코호트 분석).

    Args:
        data: {
            "cohorts": ["2024-01", "2024-02", "2024-03"],
            "periods": ["M0", "M1", "M2", "M3"],
            "retention_rates": [
                [100.0, 85.0, 72.0, 65.0],
                [100.0, 82.0, 68.0, None],
                [100.0, 78.0, None, None],
            ],
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

    cohorts = data.get("cohorts", [])
    periods = data.get("periods", [])
    retention_rates = data.get("retention_rates", [])

    if not cohorts or not periods or not retention_rates:
        raise ChartDataError(
            "cohort_heatmap",
            "cohorts, periods, retention_rates는 필수입니다.",
        )

    text = [
        [f"{val:.1f}%" if val is not None else "" for val in row]
        for row in retention_rates
    ]

    z_clean = [
        [val if val is not None else float("nan") for val in row]
        for row in retention_rates
    ]

    fig = go.Figure(
        go.Heatmap(
            x=periods,
            y=cohorts,
            z=z_clean,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=9, family=cfg.font),
            colorscale=[
                [0.0, c.negative],
                [0.5, c.caution],
                [1.0, c.positive],
            ],
            zmin=0,
            zmax=100,
            showscale=True,
            colorbar=dict(
                title=dict(text="%", font=dict(size=9)),
                tickfont=dict(size=8),
                len=0.8,
            ),
            hovertemplate=(
                "코호트: %{y}<br>"
                "기간: %{x}<br>"
                "리텐션: %{text}<extra></extra>"
            ),
        )
    )

    theme.apply_layout(fig, title=title, width=width, height=height)

    fig.update_xaxes(title_text="기간", showgrid=False, side="top")
    fig.update_yaxes(
        title_text="코호트",
        showgrid=False,
        autorange="reversed",
    )

    return fig
