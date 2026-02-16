"""연락처(Contact) 섹션 렌더러.

담당자 정보 그리드 + AMIC 로고를 포함하는 종료 슬라이드.
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
class ContactRenderer(BaseSectionRenderer):
    """연락처/종료 슬라이드 렌더러."""

    section_id = "contact"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        cards_html = ""
        for contact in data.contacts:
            name = html_escape(contact.name)
            title = html_escape(contact.title)
            details = []
            if contact.email:
                details.append(html_escape(contact.email))
            if contact.phone:
                details.append(html_escape(contact.phone))
            detail_str = " | ".join(details)

            cards_html += f"""
            <div style="text-align:center;margin-bottom:1.2em;">
                <div style="font-size:14pt;font-weight:bold;
                            color:{c.primary};">{name}</div>
                <div style="font-size:9pt;color:{c.text_secondary};">
                    {title}</div>
                <div style="font-size:10pt;color:{c.text_body};
                            font-family:'IBM Plex Mono',monospace;">
                    {detail_str}</div>
            </div>
            """

        content = f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;height:100%;">
            <h2 style="font-size:28pt;font-weight:bold;color:{c.primary};
                       margin-bottom:1em;">Contact</h2>
            {cards_html}
        </div>
        """

        slide = build_slide_html(
            content,
            slide_class="slide-contact",
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
        contacts_dicts = [
            {
                "name": c.name,
                "title": c.title,
                "email": c.email,
                "phone": c.phone,
            }
            for c in data.contacts
        ]
        slide = factory.add_contact_slide(
            contacts=contacts_dicts,
            title="Contact",
        )
        return [slide]
