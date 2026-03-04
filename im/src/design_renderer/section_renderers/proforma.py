"""Pro-Forma 섹션 렌더러 — 사업계획 + 재무제표.

TM 전용. financial_statements(projected) 데이터를 활용하여
대상회사의 Pro-Forma 사업계획과 재무제표를 표시.
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
from src.design_renderer.section_renderers.format_utils import fmt_amount, fmt_pct

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pro-Forma 사업계획
# ---------------------------------------------------------------------------


@register_renderer
class ProformaPlanRenderer(BaseSectionRenderer):
    """대상회사 Pro-Forma 사업계획 슬라이드 렌더러.

    내러티브 중심 + 핵심 KPI 요약.
    """

    section_id = "proforma_plan"

    def _build_kpis(self, data: IMDocumentData) -> list[dict[str, str]]:
        fs = data.financial_statements
        dm = data.derived_metrics or {}
        kpis: list[dict[str, str]] = []
        years = fs.years
        if years:
            latest = years[-1]
            if fs.revenue.get(latest) is not None:
                kpis.append(
                    {
                        "label": f"매출액 ({latest})",
                        "value": f"{fmt_amount(fs.revenue[latest])}억원",
                    }
                )
            if fs.operating_income.get(latest) is not None:
                kpis.append(
                    {
                        "label": f"영업이익 ({latest})",
                        "value": f"{fmt_amount(fs.operating_income[latest])}억원",
                    }
                )
            if fs.ebitda.get(latest) is not None:
                kpis.append(
                    {
                        "label": f"EBITDA ({latest})",
                        "value": f"{fmt_amount(fs.ebitda[latest])}억원",
                    }
                )
        if dm.get("revenue_cagr_3y") is not None:
            kpis.append(
                {
                    "label": "매출 CAGR (3Y)",
                    "value": fmt_pct(dm["revenue_cagr_3y"]),
                }
            )
        if dm.get("ebitda_margin_latest") is not None:
            kpis.append(
                {
                    "label": "EBITDA 마진율",
                    "value": fmt_pct(dm["ebitda_margin_latest"]),
                }
            )
        return kpis

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(data.narratives.get("proforma_plan", ""))
        kpis = self._build_kpis(data)

        kpi_html = ""
        if kpis:
            cards = ""
            for kpi in kpis:
                cards += (
                    f'<div style="text-align:center;padding:0.5em;'
                    f'background:{c.bg_cool_grey};border-radius:4px;">'
                    f'<div style="font-size:8pt;color:{c.text_secondary};">'
                    f"{html_escape(kpi['label'])}</div>"
                    f'<div style="font-size:16pt;font-weight:bold;'
                    f"color:{c.primary};font-family:'IBM Plex Mono',monospace;\">"
                    f"{html_escape(kpi['value'])}</div></div>"
                )
            kpi_html = (
                f'<div style="display:grid;grid-template-columns:'
                f"repeat({min(len(kpis), 4)}, 1fr);gap:0.6em;"
                f'margin-bottom:1em;">{cards}</div>'
            )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;">{narrative}</p>'
            )

        content = f"{kpi_html}{narrative_html}"

        return [
            build_slide_html(
                content,
                title="대상회사 Pro-Forma 사업계획",
                slide_class="slide-proforma-plan",
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
        )

        slide = factory.add_content_slide(title="대상회사 Pro-Forma 사업계획")
        narrative = data.narratives.get("proforma_plan", "")
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


# ---------------------------------------------------------------------------
# Pro-Forma 재무제표
# ---------------------------------------------------------------------------


@register_renderer
class ProformaFinancialsRenderer(BaseSectionRenderer):
    """대상회사 Pro-Forma 재무제표 슬라이드 렌더러.

    손익계산서 테이블 + 차트.
    """

    section_id = "proforma_financials"

    def _build_financial_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        fs = data.financial_statements
        years = fs.years
        headers = ["항목"] + years

        items = [
            ("매출액", fs.revenue),
            ("매출원가", fs.cost_of_goods_sold),
            ("매출총이익", fs.gross_profit),
            ("판관비", fs.sga_expenses),
            ("영업이익", fs.operating_income),
            ("EBITDA", fs.ebitda),
            ("순이익", fs.net_income),
        ]

        rows: list[dict[str, Any]] = []
        for label, source in items:
            if any(source.get(y) is not None for y in years):
                row: dict[str, Any] = {"label": label}
                for y in years:
                    row[y] = source.get(y)
                rows.append(row)
        return headers, rows

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        headers, rows = self._build_financial_rows(data)

        if not rows:
            narrative = html_escape(data.narratives.get("proforma_financials", ""))
            if narrative:
                content = (
                    f'<p style="font-size:10pt;color:{c.text_body};'
                    f'line-height:1.6;">{narrative}</p>'
                )
            else:
                content = (
                    f'<p style="font-size:10pt;color:{c.text_secondary};'
                    f'font-style:italic;">재무 데이터가 제공되지 않았습니다.</p>'
                )
            return [
                build_slide_html(
                    content,
                    title="대상회사 Pro-Forma 재무제표",
                    slide_class="slide-proforma-financials",
                    tokens=tokens,
                )
            ]

        # 테이블 빌드
        th_html = "".join(
            f'<th style="padding:5px 8px;background:{c.table_header_bg};'
            f"color:{c.text_white};font-size:9pt;"
            f'text-align:{"left" if i == 0 else "right"};">'
            f"{html_escape(h)}</th>"
            for i, h in enumerate(headers)
        )
        tr_html = ""
        for r_idx, row in enumerate(rows):
            bg = c.table_alt_row_bg if r_idx % 2 == 1 else c.bg_white
            cells = (
                f'<td style="padding:4px 8px;font-size:9pt;'
                f'font-weight:bold;color:{c.primary};background:{bg};">'
                f"{html_escape(row['label'])}</td>"
            )
            for h in headers[1:]:
                val = row.get(h)
                cells += (
                    f'<td style="padding:4px 8px;font-size:9pt;'
                    f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                    f'color:{c.text_body};background:{bg};">'
                    f"{fmt_amount(val)}</td>"
                )
            tr_html += f"<tr>{cells}</tr>"

        table_html = (
            f'<table style="border-collapse:collapse;width:100%;">'
            f"<thead><tr>{th_html}</tr></thead>"
            f"<tbody>{tr_html}</tbody></table>"
        )

        return [
            build_slide_html(
                table_html,
                title="대상회사 Pro-Forma 재무제표",
                slide_class="slide-proforma-financials",
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
            add_financial_table,
        )

        slide = factory.add_content_slide(title="대상회사 Pro-Forma 재무제표")
        headers, rows = self._build_financial_rows(data)

        if rows:
            add_financial_table(
                slide,
                headers=headers,
                rows=rows,
                top=lay.content_top,
                tokens=tokens,
                number_config=data.number_format,
                show_cagr=True,
            )
        else:
            narrative = data.narratives.get("proforma_financials", "")
            if narrative:
                add_body_textbox(slide, narrative, top=lay.content_top, tokens=tokens)

        return [slide]
