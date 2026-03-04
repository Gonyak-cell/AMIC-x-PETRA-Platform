"""Market Drivers 섹션 렌더러 — Key Demand Driver + Key Supply Driver.

시장 수요/공급 측면의 핵심 드라이버를 분석하는 TM 전용 섹션.
market_data 및 narratives 데이터 활용.
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


# ---------------------------------------------------------------------------
# Market Outlook (시장 전망)
# ---------------------------------------------------------------------------


@register_renderer
class MarketOutlookRenderer(BaseSectionRenderer):
    """Market Outlook 슬라이드 렌더러.

    기존 market_overview와 유사하지만 TM 전용 타이틀/구성.
    """

    section_id = "market_outlook"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        md = data.market_data
        narrative = html_escape(data.narratives.get("market_outlook", ""))

        # KPI 카드
        kpi_html = ""
        kpis: list[tuple[str, str]] = []
        if md:
            if md.tam is not None:
                kpis.append(("TAM", f"{md.tam:,.0f}억원"))
            if md.sam is not None:
                kpis.append(("SAM", f"{md.sam:,.0f}억원"))
            if md.som is not None:
                kpis.append(("SOM", f"{md.som:,.0f}억원"))
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
                    f'<div style="font-size:18pt;font-weight:bold;'
                    f"color:{c.primary};font-family:'IBM Plex Mono',monospace;\">"
                    f"{html_escape(value)}</div></div>"
                )
            kpi_html = (
                f'<div style="display:grid;grid-template-columns:'
                f"repeat({min(len(kpis), 4)}, 1fr);gap:0.8em;"
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
                f'color:{c.primary};margin-bottom:0.4em;">산업 트렌드</div>'
                f'<ul style="margin:0;padding-left:1.2em;">{items}</ul></div>'
            )

        content = f"""
        {kpi_html}
        {narrative_html}
        {trends_html}
        """

        return [
            build_slide_html(
                content,
                title="Market Outlook",
                slide_class="slide-market-outlook",
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
            add_bullet_list,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Market Outlook")
        md = data.market_data
        narrative = data.narratives.get("market_outlook", "")

        y = lay.content_top

        # KPI
        kpis: list[dict[str, str]] = []
        if md:
            if md.tam is not None:
                kpis.append({"label": "TAM", "value": f"{md.tam:,.0f}억원"})
            if md.sam is not None:
                kpis.append({"label": "SAM", "value": f"{md.sam:,.0f}억원"})
            if md.som is not None:
                kpis.append({"label": "SOM", "value": f"{md.som:,.0f}억원"})
            if md.market_cagr is not None:
                kpis.append(
                    {
                        "label": "시장 CAGR",
                        "value": f"{md.market_cagr * 100:.1f}%",
                    }
                )

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
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        if md and md.industry_trends:
            add_sub_header_bar(slide, "산업 트렌드", top=y, tokens=tokens)
            y += 0.45
            add_bullet_list(slide, md.industry_trends, top=y, height=2.0, tokens=tokens)

        return [slide]


# ---------------------------------------------------------------------------
# Key Demand Driver (핵심 수요 드라이버)
# ---------------------------------------------------------------------------


@register_renderer
class DemandDriverRenderer(BaseSectionRenderer):
    """Key Demand Driver 슬라이드 렌더러."""

    section_id = "demand_driver"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("demand_driver", ""))
        md = data.market_data

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        # 시장 성장 지표
        growth_html = ""
        if md:
            items: list[tuple[str, str]] = []
            if md.market_cagr is not None:
                items.append(("시장 CAGR", f"{md.market_cagr * 100:.1f}%"))
            if md.market_growth_rate is not None:
                items.append(("연 성장률", f"{md.market_growth_rate * 100:.1f}%"))
            if md.tam is not None:
                items.append(("TAM", f"{md.tam:,.0f}억원"))

            if items:
                cards = ""
                for label, value in items:
                    cards += (
                        f'<div style="padding:0.6em;background:{c.bg_light_green};'
                        f'border-radius:4px;text-align:center;">'
                        f'<div style="font-size:9pt;color:{c.text_secondary};">'
                        f"{html_escape(label)}</div>"
                        f'<div style="font-size:14pt;font-weight:bold;'
                        f'color:{c.primary};">{html_escape(value)}</div></div>'
                    )
                growth_html = (
                    f'<div style="display:grid;grid-template-columns:'
                    f"repeat({min(len(items), 3)}, 1fr);gap:0.8em;"
                    f'margin-bottom:1em;">{cards}</div>'
                )

        content = f"""
        {growth_html}
        {narrative_html}
        """

        return [
            build_slide_html(
                content,
                title="Key Demand Driver",
                slide_class="slide-demand-driver",
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

        slide = factory.add_content_slide(title="Key Demand Driver")
        md = data.market_data
        narrative = data.narratives.get("demand_driver", "")

        y = lay.content_top

        # 성장 지표 KPI
        kpis: list[dict[str, str]] = []
        if md:
            if md.market_cagr is not None:
                kpis.append(
                    {
                        "label": "시장 CAGR",
                        "value": f"{md.market_cagr * 100:.1f}%",
                    }
                )
            if md.market_growth_rate is not None:
                kpis.append(
                    {
                        "label": "연 성장률",
                        "value": f"{md.market_growth_rate * 100:.1f}%",
                    }
                )
            if md.tam is not None:
                kpis.append({"label": "TAM", "value": f"{md.tam:,.0f}억원"})

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
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        return [slide]


# ---------------------------------------------------------------------------
# Key Supply Driver (핵심 공급 드라이버)
# ---------------------------------------------------------------------------


@register_renderer
class SupplyDriverRenderer(BaseSectionRenderer):
    """Key Supply Driver 슬라이드 렌더러."""

    section_id = "supply_driver"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("supply_driver", ""))
        md = data.market_data

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        # 경쟁사 현황 (공급 측면)
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
                    f'text-align:right;color:{c.text_body};">{rev_str}</td>'
                    f'<td style="padding:5px 10px;font-size:9pt;'
                    f'text-align:right;color:{c.text_body};">{ms_str}</td></tr>'
                )
            competitor_html = (
                f'<div style="margin-bottom:1em;">'
                f'<div style="font-size:11pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">공급 환경 (경쟁사)</div>'
                f'<table style="border-collapse:collapse;width:100%;">'
                f"<thead><tr>"
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:left;">기업명</th>'
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:right;">매출액</th>'
                f'<th style="padding:6px 10px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;text-align:right;">점유율</th>'
                f"</tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
            )

        content = f"""
        {narrative_html}
        {competitor_html}
        """

        return [
            build_slide_html(
                content,
                title="Key Supply Driver",
                slide_class="slide-supply-driver",
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
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Key Supply Driver")
        md = data.market_data
        narrative = data.narratives.get("supply_driver", "")

        y = lay.content_top

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        # 경쟁사 정보 (공급 환경)
        if md and md.competitors:
            comp_lines = []
            for comp in md.competitors:
                name = comp.get("name", "")
                rev = comp.get("revenue")
                ms = comp.get("market_share")
                parts = [name]
                if rev is not None:
                    parts.append(f"매출 {rev:,.0f}")
                if ms is not None:
                    parts.append(f"점유율 {ms * 100:.1f}%")
                comp_lines.append(" | ".join(parts))
            add_sub_header_bar(slide, "공급 환경 (경쟁사)", top=y, tokens=tokens)
            y += 0.45
            add_body_textbox(slide, "\n".join(comp_lines), top=y, tokens=tokens)

        return [slide]
