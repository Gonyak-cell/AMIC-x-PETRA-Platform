"""부록(Appendix) 섹션 렌더러.

출처 목록, 추가 재무 데이터, 용어 설명 등 부록 콘텐츠.
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
class AppendixRenderer(BaseSectionRenderer):
    """부록 슬라이드 렌더러."""

    section_id = "appendix"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("appendix", ""))

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        # 출처 목록
        sources_html = ""
        if data.source_citations:
            items = ""
            for section_id, citations in data.source_citations.items():
                for citation in citations:
                    source = html_escape(citation.source_name)
                    date = html_escape(citation.access_date)
                    doc_title = (
                        html_escape(citation.document_title)
                        if citation.document_title
                        else ""
                    )

                    detail = source
                    if doc_title:
                        detail += f" — {doc_title}"
                    if date:
                        detail += f" (접근일: {date})"

                    items += (
                        f'<li style="font-size:9pt;color:{c.text_body};'
                        f'margin-bottom:0.4em;">{detail}</li>'
                    )

            if items:
                sources_html = (
                    f'<div style="margin-bottom:1em;">'
                    f'<div style="font-size:11pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.4em;">'
                    f"출처 및 참고자료</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">'
                    f"{items}</ul></div>"
                )

        # 추가 재무 데이터 (extra)
        extra_html = ""
        fs = data.financial_statements
        if fs.extra:
            extra_items = ""
            years = fs.years
            for item_name, yearly in fs.extra.items():
                vals = " | ".join(
                    f"{y}: {yearly.get(y, 'N/A'):,.0f}"
                    if isinstance(yearly.get(y), (int, float))
                    else f"{y}: N/A"
                    for y in years
                )
                extra_items += (
                    f'<li style="font-size:9pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">'
                    f'<span style="font-weight:bold;">'
                    f"{html_escape(item_name)}</span>: {vals}</li>"
                )

            if extra_items:
                extra_html = (
                    f'<div style="margin-bottom:1em;">'
                    f'<div style="font-size:11pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.4em;">'
                    f"추가 재무 데이터</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">'
                    f"{extra_items}</ul></div>"
                )

        content = f"""
        {narrative_html}
        {sources_html}
        {extra_html}
        """

        slide = build_slide_html(
            content,
            title="Appendix",
            slide_class="slide-appendix",
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
        )

        slide = factory.add_content_slide(title="Appendix")
        narrative = data.narratives.get("appendix", "")

        y = lay.content_top

        if narrative:
            add_body_textbox(slide, narrative, top=y, height=1.0, tokens=tokens)
            y += 1.2

        # 출처 목록
        if data.source_citations:
            source_items: list[str] = []
            for section_id, citations in data.source_citations.items():
                for citation in citations:
                    detail = citation.source_name
                    if citation.document_title:
                        detail += f" — {citation.document_title}"
                    if citation.access_date:
                        detail += f" ({citation.access_date})"
                    source_items.append(detail)

            if source_items:
                add_sub_header_bar(
                    slide, "출처 및 참고자료", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide, source_items, top=y, height=3.0, tokens=tokens
                )

        return [slide]
