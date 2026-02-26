"""DM Market & Transaction Trends 렌더러.

시장 동향 및 M&A 거래 트렌드를 분석하는 DM 전용 섹션.
market_data + narratives 데이터 활용.
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
class DmMarketTrendsRenderer(BaseSectionRenderer):
    """Market & Transaction Trends 슬라이드 렌더러."""

    section_id = "dm_market_trends"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        md = data.market_data
        narrative = html_escape(data.narratives.get("dm_market_trends", ""))

        # KPI 카드
        kpi_html = ""
        kpis: list[tuple[str, str]] = []
        if md:
            if md.tam is not None:
                kpis.append(("시장 규모 (TAM)", f"{md.tam:,.0f}억원"))
            if md.market_cagr is not None:
                kpis.append(("시장 CAGR", f"{md.market_cagr * 100:.1f}%"))
            elif md.market_growth_rate is not None:
                kpis.append(("시장 성장률", f"{md.market_growth_rate * 100:.1f}%"))

        if kpis:
            cards = ""
            for label, value in kpis:
                cards += (
                    f'<div style="text-align:center;padding:0.6em;'
                    f'background:{c.bg_light_green};border-radius:4px;">'
                    f'<div style="font-size:9pt;color:{c.text_secondary};">'
                    f"{html_escape(label)}</div>"
                    f'<div style="font-size:14pt;font-weight:bold;'
                    f'color:{c.primary};">{html_escape(value)}</div></div>'
                )
            kpi_html = (
                f'<div style="display:grid;grid-template-columns:'
                f"repeat({min(len(kpis), 3)}, 1fr);gap:0.8em;"
                f'margin-bottom:1em;">{cards}</div>'
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:0.8em;">{narrative}</p>'
            )

        # 산업 트렌드
        trends_html = ""
        if md and md.industry_trends:
            items = "".join(
                f'<li style="font-size:10pt;color:{c.text_body};'
                f'margin-bottom:0.3em;">{html_escape(t)}</li>'
                for t in md.industry_trends
            )
            trends_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">주요 트렌드</div>'
                f'<ul style="margin:0;padding-left:1.2em;">{items}</ul></div>'
            )

        content = f"{kpi_html}{narrative_html}{trends_html}"
        return [build_slide_html(
            content,
            title="Market & Transaction Trends",
            slide_class="slide-dm-market-trends",
            tokens=tokens,
        )]

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
            add_bullet_list,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Market & Transaction Trends")
        md = data.market_data
        narrative = data.narratives.get("dm_market_trends", "")

        y = lay.content_top

        # KPI
        kpis: list[dict[str, str]] = []
        if md:
            if md.tam is not None:
                kpis.append({"label": "시장 규모 (TAM)", "value": f"{md.tam:,.0f}억원"})
            if md.market_cagr is not None:
                kpis.append({"label": "시장 CAGR", "value": f"{md.market_cagr * 100:.1f}%"})
            elif md.market_growth_rate is not None:
                kpis.append({"label": "시장 성장률", "value": f"{md.market_growth_rate * 100:.1f}%"})

        if kpis:
            add_kpi_grid(slide, kpis, top=y, tokens=tokens, number_config=data.number_format)
            y += 1.6

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        if md and md.industry_trends:
            add_sub_header_bar(slide, "주요 트렌드", top=y, tokens=tokens)
            y += 0.45
            add_bullet_list(slide, md.industry_trends, top=y, height=2.0, tokens=tokens)

        return [slide]
