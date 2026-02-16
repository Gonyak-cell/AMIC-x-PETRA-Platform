"""거래 구조(Transaction Structure) 섹션 렌더러.

구주/신주 규모, 밸류에이션, 거래 방식 등 거래 구조 상세 정보.
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
class TransactionStructureRenderer(BaseSectionRenderer):
    """거래 구조 슬라이드 렌더러."""

    section_id = "transaction_structure"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        ds = data.deal_structure
        narrative = html_escape(
            data.narratives.get("transaction_structure", "")
        )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        structure_html = ""
        if ds:
            items = []

            if ds.transaction_type:
                items.append(("거래 유형", ds.transaction_type.value))
            if ds.seller:
                items.append(("매각주체", ds.seller))
            if ds.stake_pct is not None:
                items.append(("매각 지분율", f"{ds.stake_pct * 100:.1f}%"))
            if ds.old_shares is not None:
                items.append(("구주 규모", f"{ds.old_shares:,.0f}억원"))
            if ds.new_shares is not None:
                items.append(("신주 규모", f"{ds.new_shares:,.0f}억원"))

            # 밸류에이션
            if ds.valuation_low is not None or ds.valuation_high is not None:
                if ds.valuation_low is not None and ds.valuation_high is not None:
                    val_str = (
                        f"{ds.valuation_low:,.0f} ~ "
                        f"{ds.valuation_high:,.0f}억원"
                    )
                elif ds.valuation_low is not None:
                    val_str = f"{ds.valuation_low:,.0f}억원~"
                else:
                    val_str = f"~{ds.valuation_high:,.0f}억원"
                items.append(("밸류에이션 범위", val_str))

            if ds.valuation_method:
                items.append(("밸류에이션 방법론", ds.valuation_method))

            if items:
                # 카드 그리드
                cards = ""
                for label, value in items:
                    cards += (
                        f'<div style="padding:0.6em;background:{c.bg_cool_grey};'
                        f'border-radius:4px;border-left:3px solid {c.accent};">'
                        f'<div style="font-size:9pt;color:{c.text_secondary};">'
                        f"{html_escape(label)}</div>"
                        f'<div style="font-size:12pt;font-weight:bold;'
                        f'color:{c.primary};margin-top:2px;">'
                        f"{html_escape(value)}</div></div>"
                    )
                cols = min(len(items), 3)
                structure_html = (
                    f'<div style="display:grid;grid-template-columns:'
                    f"repeat({cols}, 1fr);gap:0.8em;"
                    f'margin-bottom:1em;">{cards}</div>'
                )

        # 타임라인
        timeline_html = ""
        if ds and ds.timeline:
            items_html = ""
            for milestone, date_val in ds.timeline.items():
                items_html += (
                    f'<div style="display:flex;align-items:center;'
                    f'margin-bottom:0.5em;">'
                    f'<div style="width:10px;height:10px;border-radius:50%;'
                    f'background:{c.accent};margin-right:0.8em;'
                    f'flex-shrink:0;"></div>'
                    f'<div>'
                    f'<span style="font-weight:bold;font-size:10pt;'
                    f'color:{c.primary};">{html_escape(milestone)}</span>'
                    f'<span style="font-size:9pt;color:{c.text_secondary};'
                    f'margin-left:0.5em;">{html_escape(date_val)}</span>'
                    f"</div></div>"
                )
            timeline_html = (
                f'<div style="padding:0.8em;background:{c.bg_light_green};'
                f'border-radius:4px;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.5em;">거래 일정</div>'
                f"{items_html}</div>"
            )

        content = f"""
        {narrative_html}
        {structure_html}
        {timeline_html}
        """

        slide = build_slide_html(
            content,
            title="거래 구조",
            slide_class="slide-transaction-structure",
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
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="거래 구조")
        ds = data.deal_structure
        narrative = data.narratives.get("transaction_structure", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if ds:
            kpis: list[dict[str, str]] = []
            if ds.transaction_type:
                kpis.append({
                    "label": "거래 유형",
                    "value": ds.transaction_type.value,
                })
            if ds.stake_pct is not None:
                kpis.append({
                    "label": "매각 지분율",
                    "value": f"{ds.stake_pct * 100:.1f}%",
                })
            if ds.old_shares is not None:
                kpis.append({
                    "label": "구주 규모",
                    "value": f"{ds.old_shares:,.0f}억원",
                })
            if ds.new_shares is not None:
                kpis.append({
                    "label": "신주 규모",
                    "value": f"{ds.new_shares:,.0f}억원",
                })

            if kpis:
                add_kpi_grid(
                    slide, kpis, top=y, tokens=tokens,
                    number_config=data.number_format,
                )
                y += 1.6

            # 밸류에이션 + 거래 일정
            detail_lines = []
            if ds.valuation_method:
                detail_lines.append(f"밸류에이션 방법론: {ds.valuation_method}")
            if ds.valuation_low is not None and ds.valuation_high is not None:
                detail_lines.append(
                    f"밸류에이션 범위: {ds.valuation_low:,.0f} ~ "
                    f"{ds.valuation_high:,.0f}억원"
                )
            if ds.deal_background:
                detail_lines.append(f"거래 배경: {ds.deal_background}")
            if ds.timeline:
                for milestone, date_val in ds.timeline.items():
                    detail_lines.append(f"{milestone}: {date_val}")

            if detail_lines:
                add_sub_header_bar(
                    slide, "거래 상세", top=y, tokens=tokens
                )
                y += 0.45
                add_body_textbox(
                    slide,
                    "\n".join(detail_lines),
                    top=y,
                    tokens=tokens,
                )

        return [slide]
