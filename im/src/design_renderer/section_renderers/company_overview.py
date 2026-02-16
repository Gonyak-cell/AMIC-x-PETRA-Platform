"""회사 개요(Company Overview) 섹션 렌더러.

연혁, 사업 모델, 주요 제품, 임직원 수, 본사, 인증 등 회사 기본 정보.
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
class CompanyOverviewRenderer(BaseSectionRenderer):
    """회사 개요 슬라이드 렌더러."""

    section_id = "company_overview"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        co = data.company_overview
        narrative = html_escape(data.narratives.get("company_overview", ""))

        # 회사 기본 정보 테이블
        info_html = ""
        if co:
            rows = []
            if data.company_name_kr:
                rows.append(("회사명", data.company_name_kr))
            if co.established_date:
                rows.append(("설립일", co.established_date))
            if co.headquarters:
                rows.append(("본사", co.headquarters))
            if co.employee_count is not None:
                rows.append(("임직원 수", f"{co.employee_count:,}명"))
            if co.key_products:
                rows.append(("주요 제품/서비스", ", ".join(co.key_products)))
            if co.certifications:
                rows.append(("인증", ", ".join(co.certifications)))

            if rows:
                tr_html = ""
                for label, value in rows:
                    tr_html += (
                        f'<tr><td style="font-weight:bold;color:{c.primary};'
                        f'padding:5px 10px;font-size:10pt;width:140px;'
                        f'vertical-align:top;">{html_escape(label)}</td>'
                        f'<td style="color:{c.text_body};padding:5px 10px;'
                        f'font-size:10pt;">{html_escape(value)}</td></tr>'
                    )
                info_html = (
                    f'<table style="border-collapse:collapse;width:100%;'
                    f'margin-bottom:1em;">{tr_html}</table>'
                )

        # 연혁
        history_html = ""
        if co and co.history:
            items = ""
            for entry in co.history:
                year = html_escape(entry.get("year", ""))
                event = html_escape(entry.get("event", ""))
                items += (
                    f'<div style="display:flex;margin-bottom:0.4em;">'
                    f'<span style="font-weight:bold;color:{c.primary};'
                    f'min-width:60px;font-size:10pt;">{year}</span>'
                    f'<span style="color:{c.text_body};font-size:10pt;">'
                    f"{event}</span></div>"
                )
            history_html = (
                f'<div style="margin-top:0.8em;padding:0.8em;'
                f'background:{c.bg_cool_grey};border-radius:4px;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.5em;">연혁</div>'
                f"{items}</div>"
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:0.8em;">{narrative}</p>'
            )

        content = f"""
        {narrative_html}
        {info_html}
        {history_html}
        """

        slide = build_slide_html(
            content,
            title="회사 개요",
            slide_class="slide-company-overview",
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

        slide = factory.add_content_slide(title="회사 개요")
        co = data.company_overview
        narrative = data.narratives.get("company_overview", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if co:
            # 회사 기본 정보
            info_lines = []
            if data.company_name_kr:
                info_lines.append(f"회사명: {data.company_name_kr}")
            if co.established_date:
                info_lines.append(f"설립일: {co.established_date}")
            if co.headquarters:
                info_lines.append(f"본사: {co.headquarters}")
            if co.employee_count is not None:
                info_lines.append(f"임직원 수: {co.employee_count:,}명")
            if info_lines:
                add_sub_header_bar(slide, "회사 정보", top=y, tokens=tokens)
                y += 0.45
                add_body_textbox(
                    slide, "\n".join(info_lines), top=y, height=1.2, tokens=tokens
                )
                y += 1.4

            # 주요 제품/서비스
            if co.key_products:
                add_sub_header_bar(
                    slide, "주요 제품/서비스", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide, co.key_products, top=y, height=1.5, tokens=tokens
                )

        return [slide]
