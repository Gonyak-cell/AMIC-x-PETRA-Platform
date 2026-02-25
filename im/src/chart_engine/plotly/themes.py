"""AMIC 디자인 테마 팩토리 — Plotly Figure에 일관된 스타일 적용.

> 마지막 수정: 2026-02-10 13:45:13

chart_embed.py의 _apply_amic_layout()과 _get_color_sequence()를
AMICThemeFactory 클래스로 캡슐화한다.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import DEFAULT_CHART_CONFIG, ChartConfig


class AMICThemeFactory:
    """AMIC 디자인 테마를 Plotly Figure에 적용하는 팩토리.

    Args:
        config: 차트 설정. None이면 DEFAULT_CHART_CONFIG 사용.
    """

    def __init__(self, config: ChartConfig | None = None) -> None:
        self._config = config or DEFAULT_CHART_CONFIG

    @property
    def config(self) -> ChartConfig:
        """현재 차트 설정 반환."""
        return self._config

    def apply_layout(
        self,
        fig: go.Figure,
        *,
        title: str = "",
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """AMIC 스타일 레이아웃을 Figure에 일괄 적용.

        Args:
            fig: Plotly Figure.
            title: 차트 제목 (빈 문자열이면 제목 미표시).
            width: 오버라이드 너비 (px). None이면 config.width 사용.
            height: 오버라이드 높이 (px). None이면 config.height 사용.
        """
        c = self._config.colors
        font = self._config.font
        w = width or self._config.width
        h = height or self._config.height

        title_config: dict[str, Any] | None = (
            dict(
                text=title,
                font=dict(family=font, size=14, color=c.primary),
                x=0.5,
                xanchor="center",
            )
            if title
            else None
        )

        fig.update_layout(
            title=title_config,
            font=dict(family=font, size=10, color=c.text_body),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=60, r=20, t=50 if title else 20, b=50),
            legend=dict(
                font=dict(size=9, color=c.text_secondary),
                bgcolor="rgba(0,0,0,0)",
            ),
            width=w,
            height=h,
        )

        # 축 스타일
        fig.update_xaxes(
            showgrid=True,
            gridcolor=c.gray_border,
            gridwidth=0.5,
            tickfont=dict(family=font, size=9, color=c.text_body),
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor=c.gray_border,
            gridwidth=0.5,
            tickfont=dict(family=font, size=9, color=c.text_body),
        )

    def get_color_sequence(self) -> list[str]:
        """AMIC 5단계 그린 기반 차트 컬러 시퀀스 반환."""
        c = self._config.colors
        return [
            c.primary,    # Signature Green
            c.secondary,  # Solid Green
            c.accent,     # Highlight Green
            c.fresh,      # Fresh Green
            c.gray_medium,   # 중립 그레이 (시맨틱 컬러 혼입 방지)
            c.text_secondary,
            c.bg_cool_grey,
        ]

    def get_semantic_colors(self) -> dict[str, str]:
        """시맨틱 색상 맵 반환 (positive, negative, caution 등)."""
        c = self._config.colors
        return {
            "positive": c.positive,
            "negative": c.negative,
            "caution": c.caution,
            "primary": c.primary,
            "secondary": c.secondary,
            "accent": c.accent,
            "fresh": c.fresh,
        }
