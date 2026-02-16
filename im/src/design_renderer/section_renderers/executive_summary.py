"""Executive Summary 섹션 렌더러.

AI 생성 내러티브 + 핵심 재무 KPI 하이라이트를 포함하는 요약 슬라이드.
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


def _format_pct(val: float | None) -> str:
    """퍼센트 값 포매팅."""
    if val is None:
        return "N/A"
    return f"{val * 100:.1f}%"


def _format_amount(val: float | None, scale: str = "억원") -> str:
    """금액 값 포매팅."""
    if val is None:
        return "N/A"
    return f"{val:,.0f}{scale}"


@register_renderer
class ExecutiveSummaryRenderer(BaseSectionRenderer):
    """Executive Summary 슬라이드 렌더러."""

    section_id = "executive_summary"

    def _build_kpis(self, data: IMDocumentData) -> list[dict[str, str]]:
        """KPI 데이터를 [{label, value}] 리스트로 변환."""
        fs = data.financial_statements
        dm = data.derived_metrics or {}
        years = fs.years
        kpis: list[dict[str, str]] = []

        if years:
            latest = years[-1]
            if fs.revenue.get(latest) is not None:
                kpis.append({
                    "label": f"매출액 ({latest})",
                    "value": _format_amount(fs.revenue[latest]),
                })
            if fs.operating_income.get(latest) is not None:
                kpis.append({
                    "label": f"영업이익 ({latest})",
                    "value": _format_amount(fs.operating_income[latest]),
                })
            if fs.ebitda.get(latest) is not None:
                kpis.append({
                    "label": f"EBITDA ({latest})",
                    "value": _format_amount(fs.ebitda[latest]),
                })
            if fs.net_income.get(latest) is not None:
                kpis.append({
                    "label": f"순이익 ({latest})",
                    "value": _format_amount(fs.net_income[latest]),
                })

        if dm.get("revenue_cagr_3y") is not None:
            kpis.append({
                "label": "매출 CAGR (3Y)",
                "value": _format_pct(dm["revenue_cagr_3y"]),
            })
        if dm.get("ebitda_margin_latest") is not None:
            kpis.append({
                "label": "EBITDA 마진율",
                "value": _format_pct(dm["ebitda_margin_latest"]),
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

        narrative = html_escape(data.narratives.get("executive_summary", ""))
        kpis = self._build_kpis(data)

        # KPI 그리드
        kpi_html = ""
        if kpis:
            cards = ""
            for kpi in kpis:
                cards += (
                    f'<div style="text-align:center;padding:0.6em;'
                    f'background:{c.bg_cool_grey};border-radius:4px;">'
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

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.7;">{narrative}</p>'
            )

        content = f"""
        {kpi_html}
        {narrative_html}
        """

        slide = build_slide_html(
            content,
            title="Executive Summary",
            slide_class="slide-executive-summary",
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
            add_summary_textbox,
        )

        slide = factory.add_content_slide(title="Executive Summary")
        narrative = data.narratives.get("executive_summary", "")
        kpis = self._build_kpis(data)

        y = lay.content_top

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
            add_body_textbox(slide, narrative, top=y, tokens=tokens)

        return [slide]
