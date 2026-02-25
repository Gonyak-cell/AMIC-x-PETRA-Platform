"""투자 포인트(Investment Highlights) 섹션 렌더러.

투자 매력 포인트를 불릿 리스트 + 서브헤더 형식으로 표시.
3개 이상이면 Overview 슬라이드 + 개별 Highlight 슬라이드로 분리 (최대 5페이지).
"""

from __future__ import annotations

import logging
from html import escape as html_escape
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData

from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer

logger = logging.getLogger(__name__)


@register_renderer
class InvestmentHighlightsRenderer(BaseSectionRenderer):
    """투자 포인트 슬라이드 렌더러."""

    section_id = "investment_highlights"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        raise NotImplementedError("PDF output removed")

    # ------------------------------------------------------------------
    # PPTX helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_title_detail(text: str) -> tuple[str, str]:
        """Highlight 문자열을 제목/상세로 분리.

        첫 마침표(.) 또는 줄바꿈(\\n) 전까지를 제목으로, 나머지를 상세로 분리한다.
        분리 불가하면 전체 텍스트를 제목으로, 상세는 빈 문자열로 반환한다.
        """
        for sep in (".", "\n"):
            idx = text.find(sep)
            if idx != -1:
                title = text[: idx + 1].strip() if sep == "." else text[:idx].strip()
                detail = text[idx + 1 :].strip()
                if title:
                    return title, detail
        return text.strip(), ""

    def _render_single_slide(
        self,
        factory: Any,
        highlights: list[str],
        narrative: str,
        tokens: Any,
    ) -> list[Any]:
        """2개 이하 — 기존과 동일한 1-슬라이드 레이아웃."""
        from src.design_renderer.pptx_engine.shape_builder import (
            add_bullet_list,
            add_summary_textbox,
        )

        lay = tokens.layout
        slide = factory.add_content_slide(title="Investment Highlights")
        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if highlights:
            numbered = [f"{i}. {item}" for i, item in enumerate(highlights, 1)]
            add_bullet_list(slide, numbered, top=y, height=4.0, tokens=tokens)

        return [slide]

    def _render_multi_slides(
        self,
        factory: Any,
        highlights: list[str],
        narrative: str,
        tokens: Any,
    ) -> list[Any]:
        """3개 이상 — Overview 1장 + 개별 Highlight 페이지 (최대 5장)."""
        from src.design_renderer.pptx_engine.shape_builder import (
            add_body_textbox,
            add_bullet_list,
            add_sub_header_bar,
            add_summary_textbox,
        )

        lay = tokens.layout
        slides: list[Any] = []

        # ── Slide 1: Overview ──
        overview = factory.add_content_slide(title="Investment Highlights")
        y = lay.content_top

        if narrative:
            add_summary_textbox(overview, narrative, top=y, tokens=tokens)
            y += 0.7

        count = len(highlights)
        add_sub_header_bar(
            overview,
            f"Key Investment Highlights ({count})",
            top=y,
            tokens=tokens,
        )
        y += 0.45

        # Overview에 전체 포인트 요약 (번호+제목만)
        summary_items: list[str] = []
        for i, item in enumerate(highlights, 1):
            title, _detail = self._split_title_detail(item)
            summary_items.append(f"{i}. {title}")
        add_bullet_list(
            overview, summary_items, top=y, height=3.5, tokens=tokens
        )
        slides.append(overview)

        # ── Slide 2~N: Individual Highlights (최대 5장) ──
        for i, item in enumerate(highlights[:5], 1):
            title, detail = self._split_title_detail(item)

            detail_slide = factory.add_content_slide(
                title=f"Investment Highlight #{i}",
            )
            y = lay.content_top

            # 서브헤더 바: 포인트 번호 + 제목
            add_sub_header_bar(
                detail_slide,
                f"#{i}  {title}",
                top=y,
                tokens=tokens,
            )
            y += 0.50

            # 상세 설명
            if detail:
                add_body_textbox(
                    detail_slide,
                    detail,
                    top=y,
                    height=4.0,
                    tokens=tokens,
                )
            else:
                # 상세가 없으면 제목 전체를 본문으로 재표시
                add_body_textbox(
                    detail_slide,
                    title,
                    top=y,
                    height=4.0,
                    tokens=tokens,
                )

            slides.append(detail_slide)

        return slides

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        tokens = tokens or DEFAULT_TOKENS
        highlights = data.investment_highlights
        narrative = data.narratives.get("investment_highlights", "")

        if len(highlights) <= 2:
            return self._render_single_slide(
                factory, highlights, narrative, tokens
            )

        return self._render_multi_slides(
            factory, highlights, narrative, tokens
        )
