"""비즈니스 모델(Business Model) 섹션 렌더러.

비즈니스 모델 설명, 밸류 체인, 수익 구조 등을 표시.
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
class BusinessModelRenderer(BaseSectionRenderer):
    """비즈니스 모델 슬라이드 렌더러."""

    section_id = "business_model"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        co = data.company_overview
        narrative = html_escape(data.narratives.get("business_model", ""))

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.7;margin-bottom:1em;">{narrative}</p>'
            )

        # 비즈니스 모델 텍스트
        bm_html = ""
        if co and co.business_model:
            bm_html = (
                f'<div style="padding:0.8em;background:{c.bg_light_green};'
                f'border-radius:4px;margin-bottom:1em;'
                f'border-left:3px solid {c.accent};">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.3em;">'
                f"비즈니스 모델</div>"
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin:0;">'
                f"{html_escape(co.business_model)}</p></div>"
            )

        # 밸류 체인
        chain_html = ""
        if co and co.value_chain:
            steps = ""
            for i, step in enumerate(co.value_chain):
                arrow = (
                    f'<span style="color:{c.accent};font-size:16pt;'
                    f'margin:0 0.4em;">→</span>'
                    if i < len(co.value_chain) - 1
                    else ""
                )
                steps += (
                    f'<span style="display:inline-block;padding:4px 12px;'
                    f'background:{c.primary};color:{c.text_white};'
                    f'border-radius:3px;font-size:9pt;font-weight:bold;">'
                    f"{html_escape(step)}</span>{arrow}"
                )
            chain_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">'
                f"밸류 체인</div>"
                f'<div style="display:flex;align-items:center;'
                f'flex-wrap:wrap;gap:0.3em;">{steps}</div></div>'
            )

        content = f"""
        {narrative_html}
        {bm_html}
        {chain_html}
        """

        slide = build_slide_html(
            content,
            title="비즈니스 모델",
            slide_class="slide-business-model",
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
            add_body_textbox,
            add_bullet_list,
            add_sub_header_bar,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="비즈니스 모델")
        co = data.company_overview
        narrative = data.narratives.get("business_model", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if co and co.business_model:
            add_sub_header_bar(
                slide, "비즈니스 모델", top=y, tokens=tokens
            )
            y += 0.45
            add_body_textbox(
                slide, co.business_model, top=y, height=1.5, tokens=tokens
            )
            y += 1.7

        if co and co.value_chain:
            add_sub_header_bar(
                slide, "밸류 체인", top=y, tokens=tokens
            )
            y += 0.45
            chain_text = " → ".join(co.value_chain)
            add_body_textbox(
                slide, chain_text, top=y, height=0.5, tokens=tokens
            )

        return [slide]
