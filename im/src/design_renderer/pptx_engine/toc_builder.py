"""TOC 구분 슬라이드 생성 — BLANK 레이아웃, 현재 섹션 ALL CAPS 하이라이트.

섹션 목록을 2열 테이블 (번호+섹션명)로 배치하고,
현재 활성 섹션을 AMIC 컬러로 강조한다.
"""

from __future__ import annotations

import logging
from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

logger = logging.getLogger(__name__)

# 섹션 ID → 한글 표시명 매핑
SECTION_DISPLAY_NAMES: dict[str, str] = {
    "deal_overview": "거래 개요",
    "executive_summary": "Executive Summary",
    "investment_highlights": "투자 포인트",
    "company_overview": "회사 개요",
    "business_model": "사업 모델",
    "market_overview": "시장 분석",
    "business_overview": "사업부별 분석",
    "value_creation": "가치 창출 계획",
    "growth_strategy": "성장 전략",
    "financial_analysis": "재무 분석",
    "management_team": "경영진 소개",
    "shareholder_structure": "주주 구성",
    "transaction_structure": "거래 구조",
    "appendix": "부록",
}


def build_toc_slide(
    slide: Any,
    sections: list[str],
    current_section: str,
    *,
    tokens: IMDesignTokens | None = None,
    section_names: dict[str, str] | None = None,
) -> Any:
    """TOC 구분 슬라이드 콘텐츠 생성.

    BLANK 레이아웃 슬라이드에 "TABLE OF CONTENTS" 제목과
    섹션 목록을 배치한다. 현재 섹션은 ALL CAPS + AMIC 컬러.

    Args:
        slide: Slide 객체 (BLANK 레이아웃).
        sections: 표시할 섹션 ID 리스트 (cover/disclaimer/toc_divider/contact 제외).
        current_section: 현재 활성 섹션 ID.
        tokens: 디자인 토큰.
        section_names: 섹션 ID→표시명 매핑 오버라이드.

    Returns:
        slide 객체.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    names = section_names or SECTION_DISPLAY_NAMES
    c = tokens.colors
    t = tokens.typography
    f = tokens.font_sizes

    # TOC에서 제외할 섹션
    excluded = {"cover", "disclaimer", "toc_divider", "contact"}
    toc_sections = [s for s in sections if s not in excluded]

    if not toc_sections:
        return slide

    # "TABLE OF CONTENTS" 제목
    title_shape = slide.shapes.add_textbox(
        Inches(1.5),
        Inches(1.0),
        Inches(7.83),
        Inches(0.6),
    )
    tf = title_shape.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "TABLE OF CONTENTS"
    run.font.name = t.font_heading
    run.font.size = Pt(f.toc_heading)
    run.font.bold = True
    run.font.color.rgb = RGBColor.from_string(c.primary.lstrip("#"))

    # 섹션 목록 — 텍스트박스 기반 리스트
    list_top = 2.0
    item_height = 0.45

    for idx, section_id in enumerate(toc_sections):
        display_name = names.get(section_id, section_id)
        is_current = section_id == current_section
        y = list_top + idx * item_height

        # 번호
        num_shape = slide.shapes.add_textbox(
            Inches(1.5),
            Inches(y),
            Inches(0.5),
            Inches(item_height),
        )
        ntf = num_shape.text_frame
        p_num = ntf.paragraphs[0]
        p_num.alignment = PP_ALIGN.RIGHT
        r_num = p_num.add_run()
        r_num.text = f"{idx + 1:02d}"
        r_num.font.name = t.font_mono
        r_num.font.size = Pt(f.summary_text)
        r_num.font.bold = True
        r_num.font.color.rgb = RGBColor.from_string(
            (c.accent if is_current else c.text_secondary).lstrip("#")
        )

        # 섹션명
        name_shape = slide.shapes.add_textbox(
            Inches(2.2),
            Inches(y),
            Inches(6.0),
            Inches(item_height),
        )
        stf = name_shape.text_frame
        p_name = stf.paragraphs[0]
        r_name = p_name.add_run()
        r_name.text = display_name.upper() if is_current else display_name
        r_name.font.name = t.font_body
        r_name.font.size = Pt(f.summary_text)
        r_name.font.bold = is_current
        r_name.font.color.rgb = RGBColor.from_string(
            (c.primary if is_current else c.text_secondary).lstrip("#")
        )

        # 현재 섹션 하이라이트 바
        if is_current:
            _add_highlight_bar(slide, y, item_height, tokens)

    return slide


def build_toc_slide_html(
    sections: list[str],
    current_section: str,
    *,
    tokens: IMDesignTokens | None = None,
    section_names: dict[str, str] | None = None,
) -> str:
    """HTML TOC 구분 슬라이드 생성.

    css_generator.py의 .slide-toc 클래스를 사용한다.

    Args:
        sections: 표시할 섹션 ID 리스트.
        current_section: 현재 활성 섹션 ID.
        tokens: 디자인 토큰.
        section_names: 섹션 ID→표시명 매핑.

    Returns:
        <div class="slide slide-toc">...</div> HTML.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    from html import escape as html_escape

    names = section_names or SECTION_DISPLAY_NAMES
    excluded = {"cover", "disclaimer", "toc_divider", "contact"}
    toc_sections = [s for s in sections if s not in excluded]

    items_html = ""
    for idx, section_id in enumerate(toc_sections):
        display_name = names.get(section_id, section_id)
        is_current = section_id == current_section
        item_class = "toc-item toc-current" if is_current else "toc-item"
        text = display_name.upper() if is_current else display_name

        items_html += (
            f'<li class="{item_class}">'
            f'<span class="toc-number">{idx + 1:02d}</span>'
            f"<span>{html_escape(text)}</span>"
            f"</li>\n"
        )

    return f"""<div class="slide slide-toc">
    <div class="toc-heading">TABLE OF CONTENTS</div>
    <ul class="toc-list">
        {items_html}
    </ul>
</div>"""


def _add_highlight_bar(
    slide: Any,
    y: float,
    height: float,
    tokens: IMDesignTokens,
) -> None:
    """현재 섹션 하이라이트용 좌측 바."""
    from pptx.enum.shapes import MSO_SHAPE

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1.3),
        Inches(y),
        Inches(0.08),
        Inches(height),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor.from_string(
        tokens.colors.accent.lstrip("#")
    )
    bar.line.fill.background()
