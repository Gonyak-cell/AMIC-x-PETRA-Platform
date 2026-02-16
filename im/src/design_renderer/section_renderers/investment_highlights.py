"""투자 포인트(Investment Highlights) 섹션 렌더러.

투자 매력 포인트를 불릿 리스트 + 서브헤더 형식으로 표시.
"""

from __future__ import annotations

import logging
from html import escape as html_escape
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData
from src.design_renderer.pdf_output.html_builder import build_slide_html
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
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        highlights = data.investment_highlights
        narrative = html_escape(
            data.narratives.get("investment_highlights", "")
        )

        items_html = ""
        for i, item in enumerate(highlights, 1):
            items_html += (
                f'<div style="display:flex;align-items:flex-start;'
                f'margin-bottom:0.8em;">'
                f'<div style="min-width:32px;height:32px;border-radius:50%;'
                f"background:{c.accent};color:{c.text_white};"
                f'font-weight:bold;font-size:14pt;display:flex;'
                f'align-items:center;justify-content:center;'
                f'margin-right:0.8em;">{i}</div>'
                f'<div style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;padding-top:4px;">'
                f"{html_escape(item)}</div></div>"
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        content = f"""
        {narrative_html}
        <div style="margin-top:0.5em;">{items_html}</div>
        """

        slide = build_slide_html(
            content,
            title="Investment Highlights",
            slide_class="slide-investment-highlights",
            tokens=tokens,
        )
        return [slide]

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_bullet_list,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="Investment Highlights")
        highlights = data.investment_highlights
        narrative = data.narratives.get("investment_highlights", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if highlights:
            numbered = [f"{i}. {item}" for i, item in enumerate(highlights, 1)]
            add_bullet_list(
                slide, numbered, top=y, height=4.0, tokens=tokens
            )

        return [slide]
