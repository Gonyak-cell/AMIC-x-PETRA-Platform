"""DM Deal Structure Considerations 렌더러.

거래 구조 분석 및 고려사항을 정리하는 DM 전용 섹션.
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
class DmDealStructureRenderer(BaseSectionRenderer):
    """Deal Structure Considerations 슬라이드 렌더러."""

    section_id = "dm_deal_structure"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        ds = data.deal_structure
        narrative = html_escape(data.narratives.get("dm_deal_structure", ""))

        # 딜 구조 요약 박스
        deal_html = ""
        if ds:
            rows: list[tuple[str, str]] = []
            if ds.transaction_type:
                rows.append(("거래 유형", ds.transaction_type.value))
            if ds.seller:
                rows.append(("매각 주체", ds.seller))
            if ds.stake_pct is not None:
                rows.append(("매각 지분", f"{ds.stake_pct * 100:.1f}%"))
            if ds.valuation_method:
                rows.append(("밸류에이션 방법", ds.valuation_method))
            if ds.valuation_low is not None and ds.valuation_high is not None:
                rows.append(
                    (
                        "밸류에이션 범위",
                        f"{ds.valuation_low:,.0f} ~ {ds.valuation_high:,.0f}억원",
                    )
                )
            elif ds.valuation_low is not None:
                rows.append(("밸류에이션", f"{ds.valuation_low:,.0f}억원"))

            if rows:
                tr_items = "".join(
                    f'<tr><td style="padding:5px 10px;font-size:9pt;'
                    f'font-weight:bold;color:{c.primary};width:35%;">'
                    f"{html_escape(label)}</td>"
                    f'<td style="padding:5px 10px;font-size:9pt;'
                    f'color:{c.text_body};">{html_escape(value)}</td></tr>'
                    for label, value in rows
                )
                deal_html = (
                    f'<table style="border-collapse:collapse;width:100%;'
                    f'margin-bottom:1em;border:1px solid {c.bg_cool_grey};">'
                    f"<tbody>{tr_items}</tbody></table>"
                )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:0.8em;">{narrative}</p>'
            )

        content = f"{deal_html}{narrative_html}"
        return [
            build_slide_html(
                content,
                title="Deal Structure Considerations",
                slide_class="slide-dm-deal-structure",
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
            add_body_textbox,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Deal Structure Considerations")
        ds = data.deal_structure
        narrative = data.narratives.get("dm_deal_structure", "")

        y = lay.content_top

        # 딜 구조 KPI
        kpis: list[dict[str, str]] = []
        if ds:
            if ds.transaction_type:
                kpis.append({"label": "거래 유형", "value": ds.transaction_type.value})
            if ds.stake_pct is not None:
                kpis.append(
                    {"label": "매각 지분", "value": f"{ds.stake_pct * 100:.1f}%"}
                )
            if ds.valuation_method:
                kpis.append({"label": "밸류에이션", "value": ds.valuation_method})

        if kpis:
            add_kpi_grid(
                slide, kpis, top=y, tokens=tokens, number_config=data.number_format
            )
            y += 1.6

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        # 딜 구조 상세
        if ds:
            detail_lines: list[str] = []
            if ds.seller:
                detail_lines.append(f"매각 주체: {ds.seller}")
            if ds.deal_background:
                detail_lines.append(f"거래 배경: {ds.deal_background}")
            if ds.valuation_low is not None and ds.valuation_high is not None:
                detail_lines.append(
                    f"밸류에이션 범위: {ds.valuation_low:,.0f} ~ {ds.valuation_high:,.0f}억원"
                )

            if detail_lines:
                add_sub_header_bar(slide, "거래 구조 상세", top=y, tokens=tokens)
                y += 0.45
                add_body_textbox(slide, "\n".join(detail_lines), top=y, tokens=tokens)

        return [slide]
