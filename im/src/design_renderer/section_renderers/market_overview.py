"""시장 분석(Market Overview) 섹션 렌더러.

TAM/SAM/SOM, 시장 성장률, 경쟁사 현황, 산업 트렌드를 표시.
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
class MarketOverviewRenderer(BaseSectionRenderer):
    """시장 분석 슬라이드 렌더러."""

    section_id = "market_overview"

    def _build_market_kpis(
        self, data: IMDocumentData
    ) -> list[dict[str, str]]:
        """시장 KPI 리스트 생성."""
        md = data.market_data
        if not md:
            return []
        kpis: list[dict[str, str]] = []
        if md.tam is not None:
            kpis.append({"label": "TAM", "value": f"{md.tam:,.0f}억원"})
        if md.sam is not None:
            kpis.append({"label": "SAM", "value": f"{md.sam:,.0f}억원"})
        if md.som is not None:
            kpis.append({"label": "SOM", "value": f"{md.som:,.0f}억원"})
        if md.market_cagr is not None:
            kpis.append({
                "label": "시장 CAGR",
                "value": f"{md.market_cagr * 100:.1f}%",
            })
        elif md.market_growth_rate is not None:
            kpis.append({
                "label": "시장 성장률",
                "value": f"{md.market_growth_rate * 100:.1f}%",
            })
        return kpis

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        md = data.market_data
        narrative = html_escape(data.narratives.get("market_overview", ""))
        kpis = self._build_market_kpis(data)

        # KPI 카드
        kpi_html = ""
        if kpis:
            cards = ""
            for kpi in kpis:
                cards += (
                    f'<div style="text-align:center;padding:0.6em;'
                    f'background:{c.bg_light_green};border-radius:4px;">'
                    f'<div style="font-size:9pt;color:{c.text_secondary};">'
                    f'{html_escape(kpi["label"])}</div>'
                    f'<div style="font-size:18pt;font-weight:bold;'
                    f"color:{c.primary};font-family:'IBM Plex Mono',monospace;\">"
                    f'{html_escape(kpi["value"])}</div></div>'
                )
            kpi_html = (
                f'<div style="display:grid;grid-template-columns:'
                f"repeat({min(len(kpis), 4)}, 1fr);gap:0.8em;"
                f'margin-bottom:1em;">{cards}</div>'
            )

        # 경쟁사 테이블
        competitor_html = ""
        if md and md.competitors:
            rows = ""
            for comp in md.competitors:
                name = html_escape(comp.get("name", ""))
                rev = comp.get("revenue")
                rev_str = f"{rev:,.0f}" if rev is not None else "N/A"
                ms = comp.get("market_share")
                ms_str = f"{ms * 100:.1f}%" if ms is not None else "N/A"
                rows += (
                    f"<tr>"
                    f'<td style="padding:5px 10px;font-size:9pt;'
                    f'color:{c.text_body};">{name}</td>'
                    f'<td style="padding:5px 10px;font-size:9pt;'
                    f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                    f'color:{c.text_body};">{rev_str}</td>'
                    f'<td style="padding:5px 10px;font-size:9pt;'
                    f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                    f'color:{c.text_body};">{ms_str}</td></tr>'
                )
            competitor_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">경쟁 환경</div>'
                f'<table style="border-collapse:collapse;width:100%;">'
                f"<thead><tr>"
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:left;">기업명</th>'
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:right;">매출액</th>'
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:right;">시장 점유율</th>'
                f"</tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
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
                f'color:{c.primary};margin-bottom:0.4em;">산업 트렌드</div>'
                f'<ul style="margin:0;padding-left:1.2em;">{items}</ul></div>'
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:0.8em;">{narrative}</p>'
            )

        content = f"""
        {kpi_html}
        {narrative_html}
        {competitor_html}
        {trends_html}
        """

        slide = build_slide_html(
            content,
            title="시장 분석",
            slide_class="slide-market-overview",
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
            add_bullet_list,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="시장 분석")
        md = data.market_data
        narrative = data.narratives.get("market_overview", "")
        kpis = self._build_market_kpis(data)

        y = lay.content_top

        # KPI
        if kpis:
            add_kpi_grid(
                slide,
                kpis,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 1.6

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        # 산업 트렌드
        if md and md.industry_trends:
            add_sub_header_bar(slide, "산업 트렌드", top=y, tokens=tokens)
            y += 0.45
            add_bullet_list(
                slide, md.industry_trends, top=y, height=2.0, tokens=tokens
            )

        return [slide]
