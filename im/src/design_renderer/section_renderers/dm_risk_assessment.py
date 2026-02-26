"""DM Risk Assessment 렌더러.

리스크 요인 분석 및 완화 방안을 정리하는 DM 전용 섹션.
주로 LLM 내러티브 기반, market_data.regulatory_notes 보조 활용.
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
class DmRiskAssessmentRenderer(BaseSectionRenderer):
    """Risk Assessment 슬라이드 렌더러."""

    section_id = "dm_risk_assessment"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("dm_risk_assessment", ""))
        md = data.market_data

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        # 규제 환경 (보조 데이터)
        regulatory_html = ""
        if md and md.regulatory_notes:
            regulatory_html = (
                f'<div style="margin-bottom:1em;padding:0.6em;'
                f'background:{c.bg_light_green};border-radius:4px;'
                f'border-left:3px solid {c.secondary};">'
                f'<div style="font-size:9pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.3em;">규제 환경</div>'
                f'<div style="font-size:9pt;color:{c.text_body};'
                f'line-height:1.5;">{html_escape(md.regulatory_notes)}</div></div>'
            )

        content = f"{narrative_html}{regulatory_html}"
        if not content.strip():
            content = (
                f'<p style="font-size:10pt;color:{c.text_secondary};'
                f'font-style:italic;">리스크 분석 데이터가 생성 후 표시됩니다.</p>'
            )

        return [build_slide_html(
            content,
            title="Risk Assessment",
            slide_class="slide-dm-risk-assessment",
            tokens=tokens,
        )]

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
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Risk Assessment")
        narrative = data.narratives.get("dm_risk_assessment", "")
        md = data.market_data

        y = lay.content_top

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        # 규제 환경 보조 정보
        if md and md.regulatory_notes:
            add_sub_header_bar(slide, "규제 환경", top=y, tokens=tokens)
            y += 0.45
            add_body_textbox(slide, md.regulatory_notes, top=y, height=1.5, tokens=tokens)

        return [slide]
