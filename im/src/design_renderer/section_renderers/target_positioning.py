"""Target Positioning 섹션 렌더러.

대상회사의 시장 내 포지셔닝, 경쟁사 대비 강점 등을 표시.
company_overview + market_data.competitors 데이터 활용.
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
class TargetPositioningRenderer(BaseSectionRenderer):
    """Target Positioning 슬라이드 렌더러."""

    section_id = "target_positioning"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        co = data.company_overview
        md = data.market_data
        narrative = html_escape(data.narratives.get("target_positioning", ""))

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        # 회사 포지셔닝 카드
        position_html = ""
        items: list[tuple[str, str]] = []
        if co:
            if data.company_name_kr:
                items.append(("대상회사", data.company_name_kr))
            if co.headquarters:
                items.append(("소재지", co.headquarters))
            if co.employee_count is not None:
                items.append(("임직원", f"{co.employee_count:,}명"))
            if co.key_products:
                items.append(("핵심 제품/서비스", ", ".join(co.key_products[:3])))
        if md:
            if md.som is not None:
                items.append(("SOM", f"{md.som:,.0f}억원"))

        if items:
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
            position_html = (
                f'<div style="display:grid;grid-template-columns:'
                f"repeat({cols}, 1fr);gap:0.8em;"
                f'margin-bottom:1em;">{cards}</div>'
            )

        # 경쟁사 비교
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
                f'color:{c.primary};margin-bottom:0.4em;">경쟁사 비교</div>'
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
        {position_html}
        {competitor_html}
        """

        return [
            build_slide_html(
                content,
                title="Target Positioning",
                slide_class="slide-target-positioning",
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

        slide = factory.add_content_slide(title="Target Positioning")
        co = data.company_overview
        md = data.market_data
        narrative = data.narratives.get("target_positioning", "")

        y = lay.content_top

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        # KPI 카드
        kpis: list[dict[str, str]] = []
        if co:
            if co.key_products:
                kpis.append(
                    {
                        "label": "핵심 제품",
                        "value": ", ".join(co.key_products[:2]),
                    }
                )
            if co.employee_count is not None:
                kpis.append(
                    {
                        "label": "임직원",
                        "value": f"{co.employee_count:,}명",
                    }
                )
        if md:
            if md.som is not None:
                kpis.append({"label": "SOM", "value": f"{md.som:,.0f}억원"})

        if kpis:
            add_kpi_grid(
                slide,
                kpis,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 1.6

        # 경쟁사 정보
        if md and md.competitors:
            comp_lines = []
            for comp in md.competitors:
                name = comp.get("name", "")
                ms = comp.get("market_share")
                ms_str = f" ({ms * 100:.1f}%)" if ms is not None else ""
                comp_lines.append(f"{name}{ms_str}")
            add_sub_header_bar(slide, "경쟁사 비교", top=y, tokens=tokens)
            y += 0.45
            add_body_textbox(slide, "\n".join(comp_lines), top=y, tokens=tokens)

        return [slide]
