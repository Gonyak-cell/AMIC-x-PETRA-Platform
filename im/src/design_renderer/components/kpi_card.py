"""KPI 카드 컴포넌트 — 핵심 지표 시각화 + 듀얼 렌더링.

11pt 라벨 + 20pt 숫자 (IBM Plex Mono) 구조.
NumberFormatConfig로 숫자 포맷팅 + 조건부 색상 (양수=녹색, 음수=적색).
그리드 배치 지원 (행당 최대 4개 카드).
"""

from __future__ import annotations

import logging
from html import escape as html_escape
from typing import Any

from src.design_renderer.components.number_formatter import (
    format_currency,
    format_growth_indicator,
    format_number,
    format_percentage,
)
from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import NumberFormatConfig
from src.design_renderer.pptx_engine.font_helper import set_font_with_ea

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 구조
# ---------------------------------------------------------------------------


def _format_kpi_value(
    value: Any,
    fmt: str,
    config: NumberFormatConfig | None,
) -> str:
    """KPI 값 포맷팅.

    Args:
        value: 숫자 값.
        fmt: "currency" | "percentage" | "number" | "text"
        config: 숫자 표기 설정.

    Returns:
        포맷팅된 문자열.
    """
    if value is None:
        return "N/A"
    if fmt == "currency":
        return format_currency(value, config)
    if fmt == "percentage":
        return format_percentage(value, config)
    if fmt == "number":
        return format_number(value, config)
    return str(value)


# ---------------------------------------------------------------------------
# PPTX 렌더링
# ---------------------------------------------------------------------------


def render_kpi_grid_pptx(
    slide: Any,
    kpis: list[dict[str, Any]],
    *,
    left: float | None = None,
    top: float | None = None,
    width: float | None = None,
    cols: int = 4,
    tokens: IMDesignTokens | None = None,
    number_config: NumberFormatConfig | None = None,
) -> list[Any]:
    """PPTX 슬라이드에 KPI 카드 그리드 추가.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        kpis: KPI 데이터 리스트. 각 항목은 dict:
            {"label": "매출액", "value": 150000, "format": "currency",
             "change": 0.15, "unit": "억원"}
        left, top, width: 그리드 위치/크기 (inches).
        cols: 한 행의 카드 수 (기본 4).
        tokens: 디자인 토큰.
        number_config: 숫자 표기 설정.

    Returns:
        생성된 shape 리스트.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    lay = tokens.layout
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    grid_left = left if left is not None else lay.content_left
    grid_top = top if top is not None else lay.content_top + 0.4
    grid_width = width if width is not None else lay.content_width

    card_gap = 0.15  # inches
    card_width = (grid_width - card_gap * (cols - 1)) / cols
    card_height = 1.0  # inches

    shapes: list[Any] = []

    for i, kpi in enumerate(kpis):
        row = i // cols
        col = i % cols

        x = grid_left + col * (card_width + card_gap)
        y = grid_top + row * (card_height + card_gap)

        label = kpi.get("label", "")
        value = kpi.get("value")
        fmt = kpi.get("format", "number")
        change = kpi.get("change")

        formatted_value = _format_kpi_value(value, fmt, number_config)

        # 카드 배경 (둥근 사각형)
        from pptx.enum.shapes import MSO_SHAPE

        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x),
            Inches(y),
            Inches(card_width),
            Inches(card_height),
        )

        # 배경색
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(
            c.bg_cool_grey.lstrip("#")
        )
        shape.line.fill.background()

        # 텍스트
        tf = shape.text_frame
        tf.word_wrap = True

        # 값 (20pt, IBM Plex Mono, Bold)
        p_value = tf.paragraphs[0]
        p_value.alignment = PP_ALIGN.CENTER
        run_value = p_value.add_run()
        run_value.text = formatted_value
        set_font_with_ea(run_value, t.font_mono)
        run_value.font.size = Pt(f.kpi_value)
        run_value.font.bold = True
        run_value.font.color.rgb = RGBColor.from_string(c.primary.lstrip("#"))

        # 라벨 (11pt)
        p_label = tf.add_paragraph()
        p_label.alignment = PP_ALIGN.CENTER
        run_label = p_label.add_run()
        run_label.text = label
        set_font_with_ea(run_label, t.font_body)
        run_label.font.size = Pt(f.kpi_label)
        run_label.font.color.rgb = RGBColor.from_string(
            c.text_secondary.lstrip("#")
        )

        # 변동 지표
        if change is not None:
            change_text, change_color = format_growth_indicator(
                change, number_config
            )
            p_change = tf.add_paragraph()
            p_change.alignment = PP_ALIGN.CENTER
            run_change = p_change.add_run()
            run_change.text = change_text
            set_font_with_ea(run_change, t.font_mono)
            run_change.font.size = Pt(f.small_label)
            run_change.font.color.rgb = RGBColor.from_string(
                change_color.lstrip("#")
            )

        shapes.append(shape)

    return shapes


# ---------------------------------------------------------------------------
# HTML 렌더링
# ---------------------------------------------------------------------------


def render_kpi_grid_html(
    kpis: list[dict[str, Any]],
    *,
    cols: int = 4,
    tokens: IMDesignTokens | None = None,
    number_config: NumberFormatConfig | None = None,
) -> str:
    """HTML KPI 카드 그리드 생성.

    css_generator.py의 .kpi-card 클래스를 사용한다.

    Args:
        kpis: KPI 데이터 리스트 (PPTX와 동일 형식).
        cols: 한 행의 카드 수.
        tokens: 디자인 토큰.
        number_config: 숫자 표기 설정.

    Returns:
        HTML 그리드 문자열.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    grid_class = f"grid-{cols}col" if cols <= 4 else "grid-4col"
    cards_html = ""

    for kpi in kpis:
        label = kpi.get("label", "")
        value = kpi.get("value")
        fmt = kpi.get("format", "number")
        change = kpi.get("change")

        formatted_value = _format_kpi_value(value, fmt, number_config)

        change_html = ""
        if change is not None:
            change_text, change_color = format_growth_indicator(
                change, number_config
            )
            css_class = "positive" if change > 0 else "negative" if change < 0 else ""
            change_html = (
                f'<div class="kpi-change {css_class}">'
                f"{html_escape(change_text)}</div>"
            )

        cards_html += f"""<div class="kpi-card">
    <div class="kpi-value">{html_escape(formatted_value)}</div>
    <div class="kpi-label">{html_escape(label)}</div>
    {change_html}
</div>
"""

    return f'<div class="{grid_class}">\n{cards_html}</div>'
