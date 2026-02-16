"""TITAN 패턴 서브헤더 바 — AMIC 다크그린 배경 + 12pt Bold White 텍스트.

PPTX와 HTML 듀얼 렌더링을 지원한다.
"""

from __future__ import annotations

from html import escape as html_escape
from typing import TYPE_CHECKING, Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

if TYPE_CHECKING:
    pass


def render_sub_header_pptx(
    slide: Any,
    text: str,
    *,
    left: float = 0.5,
    top: float = 1.07,
    width: float = 9.83,
    height: float = 0.35,
    tokens: IMDesignTokens | None = None,
) -> Any:
    """PPTX 슬라이드에 컬러 직사각형 + Bold White 텍스트 삽입.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        text: 서브헤더 텍스트.
        left, top, width, height: 위치/크기 (inches).
        tokens: 디자인 토큰.

    Returns:
        생성된 shape 객체.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    # 배경 직사각형
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )

    # 배경색: AMIC 다크그린
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(
        tokens.colors.primary.lstrip("#")
    )

    # 테두리 없음
    shape.line.fill.background()

    # 텍스트
    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = text
    run.font.size = Pt(tokens.font_sizes.sub_header_bar)
    run.font.bold = True
    run.font.color.rgb = RGBColor.from_string(
        tokens.colors.text_white.lstrip("#")
    )
    run.font.name = tokens.typography.font_body

    return shape


def render_sub_header_html(
    text: str,
    *,
    tokens: IMDesignTokens | None = None,
) -> str:
    """HTML 서브헤더 바 <div> 생성.

    css_generator.py에서 정의한 `.sub-header-bar` 클래스를 사용한다.

    Args:
        text: 서브헤더 텍스트.
        tokens: 디자인 토큰 (인라인 스타일 폴백용).

    Returns:
        HTML 서브헤더 바 문자열.
    """
    escaped = html_escape(text)
    return f'<div class="sub-header-bar">{escaped}</div>'
