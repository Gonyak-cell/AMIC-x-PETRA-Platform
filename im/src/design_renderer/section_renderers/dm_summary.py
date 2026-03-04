"""DM Summary & Recommendations 렌더러.

요약 및 권고사항을 정리하는 DM 전용 섹션.
deal_structure + narratives 데이터 활용.
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
class DmSummaryRenderer(BaseSectionRenderer):
    """Summary & Recommendations 슬라이드 렌더러."""

    section_id = "dm_summary"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        ds = data.deal_structure
        narrative = html_escape(data.narratives.get("dm_summary", ""))

        # 핵심 지표 요약
        summary_html = ""
        if ds:
            items: list[tuple[str, str]] = []
            if ds.transaction_type:
                items.append(("거래 유형", ds.transaction_type.value))
            if ds.valuation_method:
                items.append(("밸류에이션", ds.valuation_method))
            if ds.stake_pct is not None:
                items.append(("지분율", f"{ds.stake_pct * 100:.1f}%"))

            if items:
                cards = ""
                for label, value in items:
                    cards += (
                        f'<div style="text-align:center;padding:0.6em;'
                        f'background:{c.bg_light_green};border-radius:4px;">'
                        f'<div style="font-size:9pt;color:{c.text_secondary};">'
                        f"{html_escape(label)}</div>"
                        f'<div style="font-size:14pt;font-weight:bold;'
                        f'color:{c.primary};">{html_escape(value)}</div></div>'
                    )
                summary_html = (
                    f'<div style="display:grid;grid-template-columns:'
                    f"repeat({min(len(items), 3)}, 1fr);gap:0.8em;"
                    f'margin-bottom:1em;">{cards}</div>'
                )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;">{narrative}</p>'
            )

        content = f"{summary_html}{narrative_html}"
        return [
            build_slide_html(
                content,
                title="Summary & Recommendations",
                slide_class="slide-dm-summary",
                tokens=tokens,
            )
        ]

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
            add_kpi_grid,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Summary & Recommendations")
        ds = data.deal_structure
        narrative = data.narratives.get("dm_summary", "")

        y = lay.content_top

        # 핵심 지표 KPI
        kpis: list[dict[str, str]] = []
        if ds:
            if ds.transaction_type:
                kpis.append({"label": "거래 유형", "value": ds.transaction_type.value})
            if ds.valuation_method:
                kpis.append({"label": "밸류에이션", "value": ds.valuation_method})
            if ds.stake_pct is not None:
                kpis.append({"label": "지분율", "value": f"{ds.stake_pct * 100:.1f}%"})

        if kpis:
            add_kpi_grid(
                slide, kpis, top=y, tokens=tokens, number_config=data.number_format
            )
            y += 1.6

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        return [slide]
