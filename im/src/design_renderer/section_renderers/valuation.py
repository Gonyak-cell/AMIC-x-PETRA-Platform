"""밸류에이션 & 투자수익(Valuation & Returns) 섹션 렌더러.

5개 슬라이드: KPI 요약, IRR/MOIC 시나리오, 민감도 히트맵, MOIC 워터폴, 엑싯 비교.

> 마지막 수정: 2026-02-11 22:00:00
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


def _fmt_multiple(val: float | None) -> str:
    """배수 포맷."""
    if val is None:
        return "N/A"
    return f"{val:.1f}x"


def _fmt_pct(val: float | None) -> str:
    """백분율 포맷."""
    if val is None:
        return "N/A"
    return f"{val:.1f}%"


def _fmt_amount(val: float | int | None) -> str:
    """금액 포맷."""
    if val is None:
        return "N/A"
    return f"{val:,.0f}"


@register_renderer
class ValuationRenderer(BaseSectionRenderer):
    """밸류에이션 & 투자수익 슬라이드 렌더러.

    슬라이드 1: Valuation Summary KPI + 내러티브
    슬라이드 2: IRR/MOIC 시나리오 테이블
    슬라이드 3: 민감도 히트맵 (차트)
    슬라이드 4: MOIC Bridge 워터폴 (차트)
    슬라이드 5: Exit 전략 비교 테이블
    """

    section_id = "valuation"

    # ------------------------------------------------------------------
    # 데이터 조립 헬퍼
    # ------------------------------------------------------------------

    def _build_valuation_kpis(
        self, data: IMDocumentData,
    ) -> list[dict[str, str]]:
        """밸류에이션 KPI 카드 데이터를 구성한다."""
        kpis: list[dict[str, str]] = []
        vd = data.valuation_data
        if vd is None:
            return kpis

        # 최신 연도 기준 배수 표시
        if vd.ev_ebitda:
            latest = sorted(vd.ev_ebitda.keys())[-1]
            kpis.append({
                "label": f"EV/EBITDA ({latest})",
                "value": _fmt_multiple(vd.ev_ebitda[latest]),
            })
        if vd.pe_ratio:
            latest = sorted(vd.pe_ratio.keys())[-1]
            kpis.append({
                "label": f"P/E ({latest})",
                "value": _fmt_multiple(vd.pe_ratio[latest]),
            })
        if vd.ev_revenue:
            latest = sorted(vd.ev_revenue.keys())[-1]
            kpis.append({
                "label": f"EV/Revenue ({latest})",
                "value": _fmt_multiple(vd.ev_revenue[latest]),
            })
        if vd.moic_scenarios.get("base") is not None:
            kpis.append({
                "label": "MOIC (Base)",
                "value": _fmt_multiple(vd.moic_scenarios["base"]),
            })
        return kpis

    def _build_scenario_table(
        self, data: IMDocumentData,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """IRR/MOIC 시나리오 테이블 데이터를 구성한다."""
        headers = ["시나리오", "Entry Multiple", "Exit Multiple",
                    "보유기간", "IRR", "MOIC"]
        rows: list[dict[str, Any]] = []
        vd = data.valuation_data
        if vd is None:
            return headers, rows

        for name, scen in vd.irr_scenarios.items():
            moic = vd.moic_scenarios.get(name)
            rows.append({
                "label": name.capitalize(),
                "Entry Multiple": _fmt_multiple(scen.get("entry_multiple")),
                "Exit Multiple": _fmt_multiple(scen.get("exit_multiple")),
                "보유기간": f"{scen.get('holding_period', 'N/A')}년",
                "IRR": _fmt_pct(scen.get("irr")),
                "MOIC": _fmt_multiple(moic) if moic else "N/A",
            })
        return headers, rows

    def _build_exit_table(
        self, data: IMDocumentData,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """엑싯 전략 비교 테이블 데이터를 구성한다."""
        headers = ["Exit Multiple", "Exit EV", "Exit Equity", "MOIC", "IRR"]
        rows: list[dict[str, Any]] = []
        vd = data.valuation_data
        if vd is None:
            return headers, rows

        for label, ea in vd.exit_analysis.items():
            rows.append({
                "label": label,
                "Exit EV": _fmt_amount(ea.get("exit_ev")),
                "Exit Equity": _fmt_amount(ea.get("exit_equity")),
                "MOIC": _fmt_multiple(ea.get("moic")),
                "IRR": _fmt_pct(ea.get("irr")),
            })
        return headers, rows

    # ------------------------------------------------------------------
    # HTML 렌더링
    # ------------------------------------------------------------------

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors
        slides: list[str] = []

        # 슬라이드 1: KPI + 내러티브
        kpis = self._build_valuation_kpis(data)
        narrative = html_escape(data.narratives.get("valuation", ""))

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

        slides.append(build_slide_html(
            f"{kpi_html}{narrative_html}",
            title="밸류에이션 요약",
            slide_class="slide-valuation",
            tokens=tokens,
        ))

        vd = data.valuation_data

        # 슬라이드 2: IRR/MOIC 시나리오 테이블
        if vd and vd.irr_scenarios:
            headers, rows = self._build_scenario_table(data)
            if rows:
                th = "".join(
                    f'<th style="padding:5px 8px;background:{c.table_header_bg};'
                    f'color:{c.text_white};font-size:9pt;">'
                    f"{html_escape(h)}</th>"
                    for h in headers
                )
                tr = ""
                for r_idx, row in enumerate(rows):
                    bg = c.table_alt_row_bg if r_idx % 2 == 1 else c.bg_white
                    cells = (
                        f'<td style="padding:4px 8px;font-size:9pt;'
                        f'font-weight:bold;color:{c.primary};background:{bg};">'
                        f'{html_escape(row["label"])}</td>'
                    )
                    for h in headers[1:]:
                        cells += (
                            f'<td style="padding:4px 8px;font-size:9pt;'
                            f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                            f'color:{c.text_body};background:{bg};">'
                            f"{html_escape(str(row.get(h, 'N/A')))}</td>"
                        )
                    tr += f"<tr>{cells}</tr>"

                slides.append(build_slide_html(
                    f'<table style="border-collapse:collapse;width:100%;">'
                    f"<thead><tr>{th}</tr></thead>"
                    f"<tbody>{tr}</tbody></table>",
                    title="IRR/MOIC 시나리오 분석",
                    slide_class="slide-valuation-scenarios",
                    tokens=tokens,
                ))

        # 슬라이드 3-4: 차트 슬라이드 (heatmap, waterfall)
        for chart in data.charts.get("valuation", []):
            chart_data = chart.data
            img = chart_data.get("image_bytes") or chart_data.get("image_path")
            if img:
                slides.append(build_slide_html(
                    f'<div style="text-align:center;"><img src="{img}" '
                    f'style="max-width:90%;max-height:80%;" /></div>',
                    title=chart.title or "밸류에이션 차트",
                    slide_class="slide-valuation-chart",
                    tokens=tokens,
                ))

        # 슬라이드 5: Exit 전략 비교
        if vd and vd.exit_analysis:
            headers, rows = self._build_exit_table(data)
            if rows:
                th = "".join(
                    f'<th style="padding:5px 8px;background:{c.table_header_bg};'
                    f'color:{c.text_white};font-size:9pt;">'
                    f"{html_escape(h)}</th>"
                    for h in headers
                )
                tr = ""
                for r_idx, row in enumerate(rows):
                    bg = c.table_alt_row_bg if r_idx % 2 == 1 else c.bg_white
                    cells = (
                        f'<td style="padding:4px 8px;font-size:9pt;'
                        f'font-weight:bold;color:{c.primary};background:{bg};">'
                        f'{html_escape(row["label"])}</td>'
                    )
                    for h in headers[1:]:
                        cells += (
                            f'<td style="padding:4px 8px;font-size:9pt;'
                            f"text-align:right;font-family:'IBM Plex Mono',monospace;"
                            f'color:{c.text_body};background:{bg};">'
                            f"{html_escape(str(row.get(h, 'N/A')))}</td>"
                        )
                    tr += f"<tr>{cells}</tr>"

                slides.append(build_slide_html(
                    f'<table style="border-collapse:collapse;width:100%;">'
                    f"<thead><tr>{th}</tr></thead>"
                    f"<tbody>{tr}</tbody></table>",
                    title="Exit 전략 비교",
                    slide_class="slide-valuation-exit",
                    tokens=tokens,
                ))

        return slides

    # ------------------------------------------------------------------
    # PPTX 렌더링
    # ------------------------------------------------------------------

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
        )

        result: list[Any] = []

        # 슬라이드 1: KPI + 내러티브
        slide1 = factory.add_content_slide(title="밸류에이션 요약")
        kpis = self._build_valuation_kpis(data)
        narrative = data.narratives.get("valuation", "")

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

        vd = data.valuation_data

        # 슬라이드 2: IRR/MOIC 시나리오 테이블
        if vd and vd.irr_scenarios:
            headers, rows = self._build_scenario_table(data)
            if rows:
                slide2 = factory.add_content_slide(
                    title="IRR/MOIC 시나리오 분석"
                )
                add_financial_table(
                    slide2,
                    headers=headers,
                    rows=rows,
                    top=lay.content_top,
                    tokens=tokens,
                    number_config=data.number_format,
                )
                result.append(slide2)

        # 슬라이드 3-4: 차트 (heatmap, waterfall)
        for chart in data.charts.get("valuation", []):
            chart_data = chart.data
            img = chart_data.get("image_bytes") or chart_data.get("image_path")
            if img:
                chart_slide = factory.add_content_slide(
                    title=chart.title or "밸류에이션 차트"
                )
                add_chart_image(
                    chart_slide, img, top=lay.content_top, tokens=tokens
                )
                result.append(chart_slide)

        # 슬라이드 5: Exit 전략 비교 테이블
        if vd and vd.exit_analysis:
            headers, rows = self._build_exit_table(data)
            if rows:
                slide_exit = factory.add_content_slide(
                    title="Exit 전략 비교"
                )
                add_financial_table(
                    slide_exit,
                    headers=headers,
                    rows=rows,
                    top=lay.content_top,
                    tokens=tokens,
                    number_config=data.number_format,
                )
                result.append(slide_exit)

        return result
