"""출처 메타데이터 → 각주 자동 생성 모듈.

크롤링/API로 수집된 데이터의 출처를 각 슬라이드 각주에 자동 삽입하여
IM 문서의 신뢰성을 높인다.
"""

from __future__ import annotations

from html import escape as html_escape
from typing import TYPE_CHECKING, Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import SourceCitation

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# 각주 텍스트 포맷팅
# ---------------------------------------------------------------------------


def format_footnote(
    citation: SourceCitation,
    number: int | None = None,
) -> str:
    """단일 출처를 각주 텍스트로 포맷팅.

    Args:
        citation: 출처 메타데이터.
        number: 각주 번호. None이면 번호 없이 포맷팅.

    Returns:
        포맷팅된 각주 텍스트.

    Examples:
        >>> format_footnote(SourceCitation(source_name="DART", access_date="2026-02"), 1)
        '1) DART (2026-02)'
    """
    parts: list[str] = []

    if number is not None:
        parts.append(f"{number})")

    parts.append(citation.source_name)

    # URL이 있으면 괄호 안에 추가
    if citation.document_title:
        parts.append(f'"{citation.document_title}"')

    # 접근일
    if citation.access_date:
        parts.append(f"({citation.access_date})")
    elif citation.url:
        parts.append(f"({citation.url})")

    return " ".join(parts)


def assign_footnote_numbers(
    citations: dict[str, list[SourceCitation]],
) -> dict[str, list[tuple[int, SourceCitation]]]:
    """전체 문서의 출처에 순차적 각주 번호 부여.

    동일한 source_name은 동일 번호를 재사용한다.
    번호는 문서 전체에서 연속 (섹션별 리셋 아님).

    Args:
        citations: {section_id: [SourceCitation, ...]}

    Returns:
        {section_id: [(footnote_number, SourceCitation), ...]}
    """
    # source_name → 번호 매핑 (중복 제거)
    name_to_number: dict[str, int] = {}
    next_number = 1

    result: dict[str, list[tuple[int, SourceCitation]]] = {}

    for section_id, section_citations in citations.items():
        numbered: list[tuple[int, SourceCitation]] = []
        for citation in section_citations:
            name = citation.source_name
            if name not in name_to_number:
                name_to_number[name] = next_number
                next_number += 1
            numbered.append((name_to_number[name], citation))
        result[section_id] = numbered

    return result


# ---------------------------------------------------------------------------
# PPTX 각주 렌더링
# ---------------------------------------------------------------------------


def render_footnote_pptx(
    slide: Any,
    citations: list[tuple[int, SourceCitation]],
    *,
    placeholder_idx: int = 12,
    tokens: IMDesignTokens | None = None,
) -> None:
    """PPTX 슬라이드의 각주 플레이스홀더(idx=12)에 출처 텍스트 삽입.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        citations: [(번호, SourceCitation), ...] 리스트.
        placeholder_idx: 각주 플레이스홀더 인덱스 (기본 12).
        tokens: 디자인 토큰.
    """
    if not citations:
        return

    if tokens is None:
        tokens = DEFAULT_TOKENS

    from pptx.dml.color import RGBColor
    from pptx.util import Pt

    # 각주 텍스트 조합
    footnote_texts = [format_footnote(c, n) for n, c in citations]
    footnote_str = "출처: " + " | ".join(footnote_texts)

    # 플레이스홀더 찾기
    ph = None
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == placeholder_idx:
            ph = shape
            break

    if ph is None:
        return

    ph.text = ""
    tf = ph.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = footnote_str
    run.font.size = Pt(tokens.font_sizes.footnote)
    run.font.color.rgb = RGBColor.from_string(tokens.colors.text_secondary.lstrip("#"))
    run.font.name = tokens.typography.font_body


# ---------------------------------------------------------------------------
# HTML 각주 렌더링
# ---------------------------------------------------------------------------


def render_footnote_html(
    citations: list[tuple[int, SourceCitation]],
    *,
    tokens: IMDesignTokens | None = None,
) -> str:
    """HTML 각주 <div> 생성.

    Args:
        citations: [(번호, SourceCitation), ...] 리스트.
        tokens: 디자인 토큰.

    Returns:
        HTML 각주 문자열. 빈 citations이면 빈 문자열.
    """
    if not citations:
        return ""

    if tokens is None:
        tokens = DEFAULT_TOKENS

    footnote_texts = [html_escape(format_footnote(c, n)) for n, c in citations]
    footnote_str = "출처: " + " | ".join(footnote_texts)

    return (
        f'<div class="slide-footnote" style="'
        f"font-size: {tokens.font_sizes.footnote}pt; "
        f"color: {tokens.colors.text_secondary};"
        f'">{footnote_str}</div>'
    )
