"""네이티브 PPTX 차트에 AMIC 디자인 토큰을 적용하는 유틸리티.

> 마지막 수정: 2026-02-27 10:28:00
"""

from __future__ import annotations

from typing import Any

from pptx.dml.color import RGBColor
from pptx.util import Pt

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG


def hex_to_rgb(hex_color: str) -> RGBColor:
    """'#RRGGBB' → pptx.dml.color.RGBColor."""
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def get_color_sequence(config: ChartConfig | None = None) -> list[str]:
    """AMIC 5단계 그린 + 특수색 시퀀스 반환."""
    c = (config or DEFAULT_CHART_CONFIG).colors
    return [
        c.primary,  # #0F3A32  Signature Green
        c.secondary,  # #1C8F57  Solid Green
        c.accent,  # #26C260  Highlight Green
        c.fresh,  # #A3E96B  Fresh Green
        c.caution,  # #EF6C00  Amber
        c.negative,  # #BC2C1A  Red
    ]


def apply_series_colors(
    chart: Any,
    config: ChartConfig | None = None,
    *,
    custom_colors: list[str] | None = None,
) -> None:
    """차트 시리즈에 AMIC 색상 팔레트 적용."""
    colors = custom_colors or get_color_sequence(config)
    plot = chart.plots[0]
    for i, series in enumerate(plot.series):
        fill = series.format.fill
        fill.solid()
        fill.fore_color.rgb = hex_to_rgb(colors[i % len(colors)])


def apply_axis_style(chart: Any, config: ChartConfig | None = None) -> None:
    """축 폰트 · 그리드 라인 스타일 적용."""
    cfg = config or DEFAULT_CHART_CONFIG
    c = cfg.colors

    for axis in (chart.value_axis, chart.category_axis):
        if axis is None:
            continue
        tl = axis.tick_labels
        tl.font.size = Pt(9)
        tl.font.color.rgb = hex_to_rgb(c.text_secondary)
        # font.name 설정은 python-pptx에서 직접 지원하지 않는 경우가 있으므로
        # 안전하게 try
        try:
            tl.font.name = cfg.font
        except AttributeError:
            pass

    # Value axis 그리드 라인
    va = chart.value_axis
    if va is not None:
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = hex_to_rgb(c.gray_border)
        va.has_minor_gridlines = False


def apply_legend(chart: Any, config: ChartConfig | None = None) -> None:
    """범례 활성화 및 스타일 적용."""
    cfg = config or DEFAULT_CHART_CONFIG
    chart.has_legend = True
    chart.legend.font.size = Pt(9)
    try:
        chart.legend.font.name = cfg.font
    except AttributeError:
        pass
    chart.legend.include_in_layout = False


def apply_data_labels(
    chart: Any,
    *,
    number_format: str = "#,##0",
    show_value: bool = True,
    font_size: int = 8,
    config: ChartConfig | None = None,
) -> None:
    """데이터 레이블 표시 설정."""
    cfg = config or DEFAULT_CHART_CONFIG
    plot = chart.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(font_size)
    dl.font.color.rgb = hex_to_rgb(cfg.colors.text_body)
    dl.number_format = number_format
    dl.number_format_is_linked = False


def apply_amic_chart_style(
    chart: Any,
    config: ChartConfig | None = None,
    *,
    show_legend: bool = True,
    custom_colors: list[str] | None = None,
) -> None:
    """네이티브 차트에 AMIC 브랜딩을 일괄 적용하는 편의 함수."""
    apply_series_colors(chart, config, custom_colors=custom_colors)
    apply_axis_style(chart, config)
    if show_legend:
        apply_legend(chart, config)
