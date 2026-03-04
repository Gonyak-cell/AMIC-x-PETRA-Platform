"""거래 개요(Deal Overview) 섹션 렌더러.

매각주체, 지분율, 거래 배경, 타임라인, 밸류에이션 등 딜 핵심 정보를 표시.
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
class DealOverviewRenderer(BaseSectionRenderer):
    """거래 개요 슬라이드 렌더러."""

    section_id = "deal_overview"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        ds = data.deal_structure
        narrative = html_escape(data.narratives.get("deal_overview", ""))

        rows_html = ""
        if ds:
            items = [
                ("거래 유형", ds.transaction_type.value if ds.transaction_type else ""),
                ("매각주체", ds.seller),
                (
                    "매각 지분율",
                    f"{ds.stake_pct * 100:.1f}%" if ds.stake_pct is not None else "",
                ),
                ("거래 배경", ds.deal_background),
                ("밸류에이션 방법론", ds.valuation_method),
            ]
            for label, value in items:
                if value:
                    rows_html += (
                        f'<tr><td style="font-weight:bold;color:{c.primary};'
                        f'padding:6px 12px;width:160px;font-size:10pt;">'
                        f"{html_escape(label)}</td>"
                        f'<td style="color:{c.text_body};padding:6px 12px;'
                        f'font-size:10pt;">{html_escape(value)}</td></tr>'
                    )

            # 밸류에이션 범위
            if ds.valuation_low is not None or ds.valuation_high is not None:
                val_str = ""
                if ds.valuation_low is not None and ds.valuation_high is not None:
                    val_str = f"{ds.valuation_low:,.0f} ~ {ds.valuation_high:,.0f}억원"
                elif ds.valuation_low is not None:
                    val_str = f"{ds.valuation_low:,.0f}억원~"
                elif ds.valuation_high is not None:
                    val_str = f"~{ds.valuation_high:,.0f}억원"
                rows_html += (
                    f'<tr><td style="font-weight:bold;color:{c.primary};'
                    f'padding:6px 12px;font-size:10pt;">밸류에이션 범위</td>'
                    f'<td style="color:{c.text_body};padding:6px 12px;'
                    f'font-size:10pt;">{html_escape(val_str)}</td></tr>'
                )

        # 타임라인
        timeline_html = ""
        if ds and ds.timeline:
            timeline_items = ""
            for milestone, date_val in ds.timeline.items():
                timeline_items += (
                    f'<div style="display:inline-block;text-align:center;'
                    f'margin-right:2em;">'
                    f'<div style="font-size:10pt;font-weight:bold;'
                    f'color:{c.primary};">{html_escape(milestone)}</div>'
                    f'<div style="font-size:9pt;color:{c.text_secondary};">'
                    f"{html_escape(date_val)}</div></div>"
                )
            timeline_html = (
                f'<div style="margin-top:1em;padding:0.8em;'
                f'background:{c.bg_cool_grey};border-radius:4px;">'
                f'<div style="font-size:10pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.5em;">거래 일정</div>'
                f"{timeline_items}</div>"
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        content = f"""
        {narrative_html}
        <table style="border-collapse:collapse;width:100%;margin-bottom:1em;">
            {rows_html}
        </table>
        {timeline_html}
        """

        slide = build_slide_html(
            content,
            title="거래 개요",
            slide_class="slide-deal-overview",
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
            add_sub_header_bar,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="거래 개요")
        ds = data.deal_structure
        narrative = data.narratives.get("deal_overview", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if ds:
            lines = []
            if ds.seller:
                lines.append(f"매각주체: {ds.seller}")
            if ds.stake_pct is not None:
                lines.append(f"매각 지분율: {ds.stake_pct * 100:.1f}%")
            if ds.transaction_type:
                lines.append(f"거래 유형: {ds.transaction_type.value}")
            if ds.deal_background:
                lines.append(f"거래 배경: {ds.deal_background}")
            if ds.valuation_method:
                lines.append(f"밸류에이션: {ds.valuation_method}")
            if ds.valuation_low is not None and ds.valuation_high is not None:
                lines.append(
                    f"밸류에이션 범위: {ds.valuation_low:,.0f} ~ "
                    f"{ds.valuation_high:,.0f}억원"
                )
            if lines:
                add_sub_header_bar(slide, "딜 구조", top=y, tokens=tokens)
                y += 0.45
                add_body_textbox(slide, "\n".join(lines), top=y, tokens=tokens)

        return [slide]
