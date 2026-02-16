"""사업 개요(Business Overview) 섹션 렌더러.

사업부별 매출 구성, 주요 고객, 사업 설명 등 사업 현황 정보.
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
class BusinessOverviewRenderer(BaseSectionRenderer):
    """사업 개요 슬라이드 렌더러."""

    section_id = "business_overview"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("business_overview", ""))

        # 사업부별 매출
        segment_html = ""
        if data.segment_revenue and data.segment_revenue.segments:
            segments = data.segment_revenue.segments
            # 연도 목록 추출
            all_years: set[str] = set()
            for yearly in segments.values():
                all_years.update(yearly.keys())
            years = sorted(all_years)

            headers = "".join(
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:right;">'
                f"{html_escape(y)}</th>"
                for y in years
            )
            rows = ""
            for seg_name, yearly in segments.items():
                cells = ""
                for y in years:
                    val = yearly.get(y)
                    cells += (
                        f'<td style="padding:5px 10px;font-size:9pt;'
                        f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                        f'color:{c.text_body};">'
                        f'{val:,.0f}' if val is not None else 'N/A'
                    )
                    cells += "</td>"
                rows += (
                    f'<tr><td style="padding:5px 10px;font-size:9pt;'
                    f'font-weight:bold;color:{c.primary};">'
                    f"{html_escape(seg_name)}</td>{cells}</tr>"
                )

            segment_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">사업부별 매출</div>'
                f'<table style="border-collapse:collapse;width:100%;">'
                f'<thead><tr><th style="padding:6px 10px;'
                f"background:{c.table_header_bg};color:{c.text_white};"
                f'font-size:9pt;text-align:left;">사업부</th>'
                f"{headers}</tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
            )

        # 주요 고객
        customer_html = ""
        if data.key_customers:
            items = "".join(
                f'<li style="font-size:10pt;color:{c.text_body};'
                f'margin-bottom:0.3em;">{html_escape(cust)}</li>'
                for cust in data.key_customers
            )
            customer_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">주요 고객</div>'
                f'<ul style="margin:0;padding-left:1.2em;">{items}</ul></div>'
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:0.8em;">{narrative}</p>'
            )

        content = f"""
        {narrative_html}
        {segment_html}
        {customer_html}
        """

        slide = build_slide_html(
            content,
            title="사업 개요",
            slide_class="slide-business-overview",
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
            add_financial_table,
            add_sub_header_bar,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="사업 개요")
        narrative = data.narratives.get("business_overview", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        # 사업부별 매출 테이블
        if data.segment_revenue and data.segment_revenue.segments:
            segments = data.segment_revenue.segments
            all_years: set[str] = set()
            for yearly in segments.values():
                all_years.update(yearly.keys())
            years = sorted(all_years)

            headers = ["사업부"] + years
            rows = []
            for seg_name, yearly in segments.items():
                row: dict[str, Any] = {"label": seg_name}
                for y_str in years:
                    row[y_str] = yearly.get(y_str)
                rows.append(row)

            add_sub_header_bar(slide, "사업부별 매출", top=y, tokens=tokens)
            y += 0.45
            add_financial_table(
                slide,
                headers=headers,
                rows=rows,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 2.5

        # 주요 고객
        if data.key_customers:
            add_sub_header_bar(slide, "주요 고객", top=y, tokens=tokens)
            y += 0.45
            add_bullet_list(
                slide, data.key_customers, top=y, height=1.5, tokens=tokens
            )

        return [slide]
