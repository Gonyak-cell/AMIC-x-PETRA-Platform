"""HTML 문서 조립 — CSS + 폰트 + 섹션별 HTML 연결.

css_generator.py가 생성한 CSS와 assets.py의 폰트 base64 인라인을
결합하여 완전한 HTML5 문서를 조립한다.
PDF 변환 (pdf_engine.py)의 입력이 된다.
"""

from __future__ import annotations

import logging
from html import escape as html_escape

from src.design_renderer.assets import generate_font_face_css
from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.pdf_output.css_generator import generate_im_css

logger = logging.getLogger(__name__)


def build_html_document(
    sections_html: list[str],
    *,
    title: str = "Information Memorandum",
    tokens: IMDesignTokens | None = None,
    extra_css: str = "",
    page_numbers: bool = True,
    total_pages: int | None = None,
) -> str:
    """완전한 HTML5 문서 조립.

    Args:
        sections_html: 섹션별 HTML 문자열 리스트.
            각 항목은 <div class="slide ...">...</div> 형태.
        title: HTML <title> 텍스트.
        tokens: 디자인 토큰.
        extra_css: 추가 CSS (섹션 렌더러별 커스텀).
        page_numbers: True이면 각 슬라이드에 페이지 번호 삽입.
        total_pages: 총 페이지 수. None이면 sections_html 길이 사용.

    Returns:
        완전한 HTML5 문서 문자열.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    if total_pages is None:
        total_pages = len(sections_html)

    # CSS 조립
    font_css = generate_font_face_css()
    layout_css = generate_im_css(tokens)

    # 페이지 번호 삽입
    if page_numbers:
        sections_html = _inject_page_numbers(
            sections_html, total_pages, tokens
        )

    body_html = "\n".join(sections_html)
    escaped_title = html_escape(title)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title}</title>
    <style>
{font_css}

{layout_css}

{extra_css}
    </style>
</head>
<body>
{body_html}
</body>
</html>"""

    logger.info(
        f"HTML 문서 조립 완료: {len(sections_html)}페이지, "
        f"총 {len(html):,}자"
    )
    return html


def build_slide_html(
    content_html: str,
    *,
    title: str = "",
    slide_class: str = "",
    tokens: IMDesignTokens | None = None,
    footnote_html: str = "",
) -> str:
    """단일 슬라이드 HTML 래퍼 생성.

    css_generator.py의 .slide 클래스를 사용하는 표준 슬라이드 구조.

    Args:
        content_html: 슬라이드 내부 콘텐츠 HTML.
        title: 슬라이드 제목 (idx=11 패턴).
        slide_class: 추가 CSS 클래스 (예: "slide-cover", "slide-toc").
        tokens: 디자인 토큰.
        footnote_html: 각주 HTML (source_citation 연동).

    Returns:
        <div class="slide">...</div> HTML 문자열.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    classes = "slide"
    if slide_class:
        classes += f" {slide_class}"

    title_html = ""
    if title:
        escaped_title = html_escape(title)
        title_html = f'<div class="slide-title">{escaped_title}</div>'

    footer_html = ""
    if footnote_html:
        footer_html = f"""<div class="slide-footer">
    <div class="slide-footnote">{footnote_html}</div>
    <div class="slide-page-number"></div>
</div>"""

    return f"""<div class="{classes}">
    {title_html}
    <div class="content-area">
        {content_html}
    </div>
    {footer_html}
</div>"""


def _inject_page_numbers(
    sections_html: list[str],
    total_pages: int,
    tokens: IMDesignTokens,
) -> list[str]:
    """각 슬라이드 HTML에 페이지 번호 삽입.

    .slide-page-number 영역의 빈 내용을 페이지 번호로 교체.
    커버 슬라이드 (첫 번째)에는 번호를 넣지 않는다.

    Args:
        sections_html: 섹션 HTML 리스트.
        total_pages: 총 페이지 수.
        tokens: 디자인 토큰.

    Returns:
        페이지 번호가 삽입된 HTML 리스트.
    """
    result: list[str] = []
    for i, html in enumerate(sections_html):
        page_num = i + 1
        if page_num == 1:
            # 커버: 페이지 번호 없음
            result.append(html)
            continue

        page_str = f"{page_num} / {total_pages}"
        # .slide-page-number 빈 div에 번호 삽입
        updated = html.replace(
            '<div class="slide-page-number"></div>',
            f'<div class="slide-page-number">{page_str}</div>',
        )
        result.append(updated)

    return result
