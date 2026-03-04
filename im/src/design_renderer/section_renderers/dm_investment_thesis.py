"""DM Investment Thesis 렌더러.

투자 근거 및 핵심 논점을 정리하는 DM 전용 섹션.
investment_highlights + narratives 데이터 활용.
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
class DmInvestmentThesisRenderer(BaseSectionRenderer):
    """Investment Thesis 슬라이드 렌더러."""

    section_id = "dm_investment_thesis"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("dm_investment_thesis", ""))
        highlights = data.investment_highlights

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        # 투자 매력 포인트
        highlights_html = ""
        if highlights:
            items = "".join(
                f'<li style="font-size:10pt;color:{c.text_body};'
                f'margin-bottom:0.4em;">{html_escape(h)}</li>'
                for h in highlights
            )
            highlights_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">핵심 투자 포인트</div>'
                f'<ul style="margin:0;padding-left:1.2em;">{items}</ul></div>'
            )

        content = f"{narrative_html}{highlights_html}"
        return [
            build_slide_html(
                content,
                title="Investment Thesis",
                slide_class="slide-dm-investment-thesis",
                tokens=tokens,
            )
        ]

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
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Investment Thesis")
        narrative = data.narratives.get("dm_investment_thesis", "")
        highlights = data.investment_highlights

        y = lay.content_top

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        if highlights:
            add_sub_header_bar(slide, "핵심 투자 포인트", top=y, tokens=tokens)
            y += 0.45
            add_bullet_list(slide, highlights, top=y, height=3.0, tokens=tokens)

        return [slide]
