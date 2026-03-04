"""밸류에이션 & 투자수익(Valuation & Returns) 섹션 렌더러.

5개 슬라이드: KPI 요약, IRR/MOIC 시나리오, 민감도 히트맵, MOIC 워터폴, 엑싯 비교.

> 마지막 수정: 2026-02-11 22:00:00
"""

from __future__ import annotations

import logging
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData

from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer
from src.design_renderer.section_renderers.format_utils import (
    fmt_amount,
    fmt_multiple,
    fmt_pct,
)

logger = logging.getLogger(__name__)


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
        self,
        data: IMDocumentData,
    ) -> list[dict[str, str]]:
        """밸류에이션 KPI 카드 데이터를 구성한다."""
        kpis: list[dict[str, str]] = []
        vd = data.valuation_data
        if vd is None:
            return kpis

        # 최신 연도 기준 배수 표시
        if vd.ev_ebitda:
            latest = sorted(vd.ev_ebitda.keys())[-1]
            kpis.append(
                {
                    "label": f"EV/EBITDA ({latest})",
                    "value": fmt_multiple(vd.ev_ebitda[latest]),
                }
            )
        if vd.pe_ratio:
            latest = sorted(vd.pe_ratio.keys())[-1]
            kpis.append(
                {
                    "label": f"P/E ({latest})",
                    "value": fmt_multiple(vd.pe_ratio[latest]),
                }
            )
        if vd.ev_revenue:
            latest = sorted(vd.ev_revenue.keys())[-1]
            kpis.append(
                {
                    "label": f"EV/Revenue ({latest})",
                    "value": fmt_multiple(vd.ev_revenue[latest]),
                }
            )
        if vd.moic_scenarios.get("base") is not None:
            kpis.append(
                {
                    "label": "MOIC (Base)",
                    "value": fmt_multiple(vd.moic_scenarios["base"]),
                }
            )
        return kpis

    def _build_scenario_table(
        self,
        data: IMDocumentData,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """IRR/MOIC 시나리오 테이블 데이터를 구성한다."""
        headers = [
            "시나리오",
            "Entry Multiple",
            "Exit Multiple",
            "보유기간",
            "IRR",
            "MOIC",
        ]
        rows: list[dict[str, Any]] = []
        vd = data.valuation_data
        if vd is None:
            return headers, rows

        for name, scen in vd.irr_scenarios.items():
            moic = vd.moic_scenarios.get(name)
            rows.append(
                {
                    "label": name.capitalize(),
                    "Entry Multiple": fmt_multiple(scen.get("entry_multiple")),
                    "Exit Multiple": fmt_multiple(scen.get("exit_multiple")),
                    "보유기간": f"{scen.get('holding_period', 'N/A')}년",
                    "IRR": fmt_pct(scen.get("irr"), already_percent=True),
                    "MOIC": fmt_multiple(moic) if moic else "N/A",
                }
            )
        return headers, rows

    def _build_exit_table(
        self,
        data: IMDocumentData,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """엑싯 전략 비교 테이블 데이터를 구성한다."""
        headers = ["Exit Multiple", "Exit EV", "Exit Equity", "MOIC", "IRR"]
        rows: list[dict[str, Any]] = []
        vd = data.valuation_data
        if vd is None:
            return headers, rows

        for label, ea in vd.exit_analysis.items():
            rows.append(
                {
                    "label": label,
                    "Exit EV": fmt_amount(ea.get("exit_ev")),
                    "Exit Equity": fmt_amount(ea.get("exit_equity")),
                    "MOIC": fmt_multiple(ea.get("moic")),
                    "IRR": fmt_pct(ea.get("irr"), already_percent=True),
                }
            )
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
        raise NotImplementedError("PDF output removed")

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
            add_chart_or_image,
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
                slide1,
                kpis,
                top=y,
                tokens=tokens,
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
                slide2 = factory.add_content_slide(title="IRR/MOIC 시나리오 분석")
                add_financial_table(
                    slide2,
                    headers=headers,
                    rows=rows,
                    top=lay.content_top,
                    tokens=tokens,
                    number_config=data.number_format,
                )
                result.append(slide2)

        # 슬라이드 3-4: 차트 (네이티브 또는 이미지)
        for chart in data.charts.get("valuation", []):
            chart_slide = factory.add_content_slide(
                title=chart.title or "밸류에이션 차트"
            )
            shape = add_chart_or_image(
                chart_slide, chart, top=lay.content_top, tokens=tokens
            )
            if shape is not None:
                result.append(chart_slide)

        # 슬라이드 5: Exit 전략 비교 테이블
        if vd and vd.exit_analysis:
            headers, rows = self._build_exit_table(data)
            if rows:
                slide_exit = factory.add_content_slide(title="Exit 전략 비교")
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
