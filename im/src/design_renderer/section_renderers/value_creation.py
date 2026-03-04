"""가치 창출(Value Creation) 섹션 렌더러.

투자 후 가치 창출 전략 및 내러티브를 표시.
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
class ValueCreationRenderer(BaseSectionRenderer):
    """가치 창출 슬라이드 렌더러."""

    section_id = "value_creation"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("value_creation", ""))
        gs = data.growth_strategy

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.7;margin-bottom:1em;">{narrative}</p>'
            )

        # 성장 전략 요소를 가치 창출 관점으로 재구성
        strategies_html = ""
        if gs:
            sections = []
            if gs.organic_growth:
                items = "".join(
                    f'<li style="font-size:10pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">{html_escape(item)}</li>'
                    for item in gs.organic_growth
                )
                sections.append(
                    f'<div style="margin-bottom:0.8em;">'
                    f'<div style="font-size:11pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.3em;">'
                    f"유기적 성장</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
                    f"</div>"
                )
            if gs.new_business:
                items = "".join(
                    f'<li style="font-size:10pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">{html_escape(item)}</li>'
                    for item in gs.new_business
                )
                sections.append(
                    f'<div style="margin-bottom:0.8em;">'
                    f'<div style="font-size:11pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.3em;">'
                    f"신규 사업</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
                    f"</div>"
                )
            if gs.ma_targets:
                items = "".join(
                    f'<li style="font-size:10pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">{html_escape(item)}</li>'
                    for item in gs.ma_targets
                )
                sections.append(
                    f'<div style="margin-bottom:0.8em;">'
                    f'<div style="font-size:11pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.3em;">'
                    f"M&amp;A 전략</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
                    f"</div>"
                )
            strategies_html = "".join(sections)

        content = f"""
        {narrative_html}
        {strategies_html}
        """

        slide = build_slide_html(
            content,
            title="가치 창출",
            slide_class="slide-value-creation",
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
            add_sub_header_bar,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="가치 창출")
        narrative = data.narratives.get("value_creation", "")
        gs = data.growth_strategy

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if gs:
            if gs.organic_growth:
                add_sub_header_bar(slide, "유기적 성장", top=y, tokens=tokens)
                y += 0.45
                add_bullet_list(
                    slide, gs.organic_growth, top=y, height=1.2, tokens=tokens
                )
                y += 1.4

            if gs.new_business:
                add_sub_header_bar(slide, "신규 사업", top=y, tokens=tokens)
                y += 0.45
                add_bullet_list(
                    slide, gs.new_business, top=y, height=1.2, tokens=tokens
                )
                y += 1.4

            if gs.ma_targets:
                add_sub_header_bar(slide, "M&A 전략", top=y, tokens=tokens)
                y += 0.45
                add_bullet_list(slide, gs.ma_targets, top=y, height=1.2, tokens=tokens)

        return [slide]
