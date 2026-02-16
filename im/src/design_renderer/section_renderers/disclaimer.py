"""면책조항(Disclaimer) 섹션 렌더러.

정형 면책조항 텍스트를 1~2 슬라이드로 렌더링.
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
class DisclaimerRenderer(BaseSectionRenderer):
    """면책조항 슬라이드 렌더러."""

    section_id = "disclaimer"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        text = data.disclaimer_text or tokens.footer_note
        escaped = html_escape(text)
        paragraphs = escaped.replace("\n", "<br>")

        content = f"""
        <p style="font-size:9pt;color:{c.text_secondary};
                  line-height:1.8;">{paragraphs}</p>
        """

        slide = build_slide_html(
            content,
            title="Disclaimer",
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
        slide = factory.add_disclaimer_slide(
            text=data.disclaimer_text or "",
            title="Disclaimer",
        )
        return [slide]
