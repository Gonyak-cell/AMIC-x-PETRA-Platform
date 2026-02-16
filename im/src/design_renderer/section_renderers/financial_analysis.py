"""재무 분석(Financial Analysis) 섹션 렌더러.

핵심 KPI + 재무 테이블 + 차트 이미지를 포함하는 다중 슬라이드 섹션.
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


def _fmt_amount(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:,.0f}"


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.1f}%"


@register_renderer
class FinancialAnalysisRenderer(BaseSectionRenderer):
    """재무 분석 슬라이드 렌더러.

    슬라이드 1: KPI 하이라이트 + 요약
    슬라이드 2: 손익계산서 테이블
    추가: 차트가 있으면 차트 슬라이드
    """

    section_id = "financial_analysis"

    def _build_kpis(self, data: IMDocumentData) -> list[dict[str, str]]:
        fs = data.financial_statements
        dm = data.derived_metrics or {}
        years = fs.years
        kpis: list[dict[str, str]] = []
        if years:
            latest = years[-1]
            if fs.revenue.get(latest) is not None:
                kpis.append({
                    "label": f"매출액 ({latest})",
                    "value": f"{_fmt_amount(fs.revenue[latest])}",
                })
            if fs.operating_income.get(latest) is not None:
                kpis.append({
                    "label": f"영업이익 ({latest})",
                    "value": f"{_fmt_amount(fs.operating_income[latest])}",
                })
            if fs.ebitda.get(latest) is not None:
                kpis.append({
                    "label": f"EBITDA ({latest})",
                    "value": f"{_fmt_amount(fs.ebitda[latest])}",
                })
            if fs.net_income.get(latest) is not None:
                kpis.append({
                    "label": f"순이익 ({latest})",
                    "value": f"{_fmt_amount(fs.net_income[latest])}",
                })
        if dm.get("operating_margin_latest") is not None:
            kpis.append({
                "label": "영업이익률",
                "value": _fmt_pct(dm["operating_margin_latest"]),
            })
        if dm.get("ebitda_margin_latest") is not None:
            kpis.append({
                "label": "EBITDA 마진율",
                "value": _fmt_pct(dm["ebitda_margin_latest"]),
            })
        if dm.get("revenue_cagr_3y") is not None:
            kpis.append({
                "label": "매출 CAGR (3Y)",
                "value": _fmt_pct(dm["revenue_cagr_3y"]),
            })
        return kpis

    def _build_financial_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """재무 테이블 headers + rows 생성."""
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

        slides: list[str] = []
        kpis = self._build_kpis(data)
        narrative = html_escape(data.narratives.get("financial_analysis", ""))
        headers, rows = self._build_financial_rows(data)

        # 슬라이드 1: KPI + 요약
        kpi_html = ""
        if kpis:
            cards = ""
            for kpi in kpis:
                cards += (
                    f'<div style="text-align:center;padding:0.5em;'
                    f'background:{c.bg_cool_grey};border-radius:4px;">'
                    f'<div style="font-size:8pt;color:{c.text_secondary};">'
                    f'{html_escape(kpi["label"])}</div>'
                    f'<div style="font-size:16pt;font-weight:bold;'
                    f"color:{c.primary};font-family:'IBM Plex Mono',monospace;\">"
                    f'{html_escape(kpi["value"])}</div></div>'
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

        content_1 = f"{kpi_html}{narrative_html}"
        slides.append(build_slide_html(
            content_1,
            title="재무 분석",
            slide_class="slide-financial-analysis",
            tokens=tokens,
        ))

        # 슬라이드 2: 재무 테이블
        if rows:
            th_html = "".join(
                f'<th style="padding:5px 8px;background:{c.table_header_bg};'
                f'color:{c.text_white};font-size:9pt;'
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
                    f'{html_escape(row["label"])}</td>'
                )
                for h in headers[1:]:
                    val = row.get(h)
                    cells += (
                        f'<td style="padding:4px 8px;font-size:9pt;'
                        f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                        f'color:{c.text_body};background:{bg};">'
                        f"{_fmt_amount(val)}</td>"
                    )
                tr_html += f"<tr>{cells}</tr>"

            table_html = (
                f'<table style="border-collapse:collapse;width:100%;">'
                f"<thead><tr>{th_html}</tr></thead>"
                f"<tbody>{tr_html}</tbody></table>"
            )
            slides.append(build_slide_html(
                table_html,
                title="손익계산서 요약",
                slide_class="slide-financial-table",
                tokens=tokens,
            ))

        return slides

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
            add_chart_image,
            add_financial_table,
            add_kpi_grid,
            add_sub_header_bar,
        )

        result: list[Any] = []

        # 슬라이드 1: KPI 하이라이트
        slide1 = factory.add_content_slide(title="재무 분석")
        kpis = self._build_kpis(data)
        narrative = data.narratives.get("financial_analysis", "")

        y = lay.content_top
        if kpis:
            add_kpi_grid(
                slide1, kpis, top=y, tokens=tokens,
                number_config=data.number_format,
            )
            y += 1.6
        if narrative:
            add_body_textbox(slide1, narrative, top=y, tokens=tokens)
        result.append(slide1)

        # 슬라이드 2: 재무 테이블
        headers, rows = self._build_financial_rows(data)
        if rows:
            slide2 = factory.add_content_slide(title="손익계산서 요약")
            add_financial_table(
                slide2,
                headers=headers,
                rows=rows,
                top=lay.content_top,
                tokens=tokens,
                number_config=data.number_format,
                show_cagr=True,
            )
            result.append(slide2)

        # 차트 슬라이드 (있으면)
        chart_list = data.charts.get("financial_analysis", [])
        for chart in chart_list:
            chart_data = chart.data
            img = chart_data.get("image_bytes") or chart_data.get("image_path")
            if img:
                chart_slide = factory.add_content_slide(
                    title=chart.title or "재무 차트"
                )
                add_chart_image(
                    chart_slide, img, top=lay.content_top, tokens=tokens
                )
                result.append(chart_slide)

        return result
