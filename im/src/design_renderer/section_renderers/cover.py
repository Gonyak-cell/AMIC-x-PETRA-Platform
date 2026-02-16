"""표지(Cover) 섹션 렌더러.

프로젝트명, 부제, 날짜, AMIC 로고, 커버 배경 이미지를 포함하는 1장 슬라이드.
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
class CoverRenderer(BaseSectionRenderer):
    """표지 슬라이드 렌더러."""

    section_id = "cover"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        project_name = html_escape(data.project_name or "Information Memorandum")
        subtitle = html_escape("Information Memorandum")
        date_str = html_escape(data.date or "")
        company = html_escape(data.company_name_kr or "")

        content = f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;height:100%;text-align:center;">
            <h1 style="font-size:40pt;font-weight:800;color:{c.primary};
                       margin-bottom:0.3em;">{project_name}</h1>
            <p style="font-size:14pt;color:{c.text_body};margin-bottom:0.2em;">
                {subtitle}</p>
            <p style="font-size:12pt;color:{c.text_secondary};">
                {company}</p>
            <p style="font-size:12pt;color:{c.text_secondary};">
                {date_str}</p>
        </div>
        """

        slide = build_slide_html(
            content,
            slide_class="slide-cover",
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
        slide = factory.add_cover_slide(
            project_name=data.project_name or "Information Memorandum",
            subtitle="Information Memorandum",
            date=data.date or "",
        )
        return [slide]
