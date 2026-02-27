"""재무 분석(Financial Analysis) 섹션 렌더러.

핵심 KPI + 재무 테이블 + 차트 이미지를 포함하는 다중 슬라이드 섹션.

슬라이드 구성 (최대 10개, 데이터 없으면 동적 스킵):
  1. Financial KPI Dashboard — 6-8 KPI 카드
  2. P&L Summary Table — 손익계산서 요약 (매출~순이익)
  3. Revenue Trend — revenue_yoy 데이터 or 매출 YoY bullet list
  4. Profitability Analysis — 영업이익률/EBITDA 마진율/순이익률 추이
  5. Balance Sheet Summary — 총자산/자기자본/부채/현금
  6. Cash Flow Analysis — 영업/투자/재무/FCF CF
  7. Working Capital — working_capital (extra 필드)
  8. CAPEX — capex 데이터
  9. Financial Ratio Dashboard — 부채비율/ROE/ROA 등 KPI 카드
 10. Chart slides — 기존 차트 이미지 삽입
"""

from __future__ import annotations

import logging
from html import escape as html_escape
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData

from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer
from src.design_renderer.section_renderers.format_utils import fmt_amount as _fmt_amount
from src.design_renderer.section_renderers.format_utils import fmt_pct as _fmt_pct

logger = logging.getLogger(__name__)


@register_renderer
class FinancialAnalysisRenderer(BaseSectionRenderer):
    """재무 분석 슬라이드 렌더러 (최대 10개 슬라이드, 데이터 기반 동적 구성).

    Slide 1:  Financial KPI Dashboard (매출/영업이익/EBITDA/순이익 + 마진율)
    Slide 2:  P&L Summary Table (손익계산서 7항목)
    Slide 3:  Revenue Trend (차트 이미지 or YoY bullet list)
    Slide 4:  Profitability Analysis (매출총이익률~순이익률 추이 테이블)
    Slide 5:  Balance Sheet Summary (총자산/부채/자기자본/차입금/현금)
    Slide 6:  Cash Flow Analysis (영업/투자/재무/FCF)
    Slide 7:  Working Capital (extra['working_capital'])
    Slide 8:  CAPEX (capex 데이터)
    Slide 9:  Financial Ratio Dashboard (부채비율/ROE/ROA 등 KPI 카드)
    Slide 10: Chart slides (나머지 차트 이미지)

    각 슬라이드는 해당 데이터가 없으면 자동 스킵된다.
    render_html()은 기존 2슬라이드 구조를 유지한다.
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

    # ------------------------------------------------------------------
    # 공통: dict[str, float] 기반 테이블 빌더
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_from_items(
        years: list[str],
        items: list[tuple[str, dict[str, float]]],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """(label, source_dict) 리스트 → (headers, rows) 변환.

        데이터가 하나도 없는 행은 자동 제외된다.
        """
        headers = ["항목"] + years
        rows: list[dict[str, Any]] = []
        for label, source in items:
            if any(source.get(y) is not None for y in years):
                row: dict[str, Any] = {"label": label}
                for y in years:
                    row[y] = source.get(y)
                rows.append(row)
        return headers, rows

    def _build_financial_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """손익계산서 테이블 headers + rows 생성 (Slide 2)."""
        fs = data.financial_statements
        return self._rows_from_items(
            fs.years,
            [
                ("매출액", fs.revenue),
                ("매출원가", fs.cost_of_goods_sold),
                ("매출총이익", fs.gross_profit),
                ("판관비", fs.sga_expenses),
                ("영업이익", fs.operating_income),
                ("EBITDA", fs.ebitda),
                ("순이익", fs.net_income),
            ],
        )

    def _build_profitability_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """수익성 분석 테이블 (Slide 4).

        각 연도의 마진율을 계산하여 행으로 만든다.
        derived_metrics 에 per-year 키가 없으므로 직접 계산한다.
        """
        fs = data.financial_statements
        years = fs.years

        # 연도별 마진율 계산
        op_margin: dict[str, float] = {}
        ebitda_margin: dict[str, float] = {}
        net_margin: dict[str, float] = {}
        gp_margin: dict[str, float] = {}

        for y in years:
            rev = fs.revenue.get(y)
            if rev is None or rev == 0:
                continue
            if fs.gross_profit.get(y) is not None:
                gp_margin[y] = fs.gross_profit[y] / rev
            if fs.operating_income.get(y) is not None:
                op_margin[y] = fs.operating_income[y] / rev
            if fs.ebitda.get(y) is not None:
                ebitda_margin[y] = fs.ebitda[y] / rev
            if fs.net_income.get(y) is not None:
                net_margin[y] = fs.net_income[y] / rev

        return self._rows_from_items(
            years,
            [
                ("매출총이익률", gp_margin),
                ("영업이익률", op_margin),
                ("EBITDA 마진율", ebitda_margin),
                ("순이익률", net_margin),
            ],
        )

    def _build_balance_sheet_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """재무상태표 요약 테이블 (Slide 5)."""
        fs = data.financial_statements
        return self._rows_from_items(
            fs.years,
            [
                ("총자산", fs.total_assets),
                ("총부채", fs.total_liabilities),
                ("자기자본", fs.total_equity),
                ("총차입금", fs.total_debt),
                ("현금성자산", fs.cash_and_equivalents),
            ],
        )

    def _build_cash_flow_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """현금흐름 분석 테이블 (Slide 6)."""
        fs = data.financial_statements
        return self._rows_from_items(
            fs.years,
            [
                ("영업활동 CF", fs.operating_cash_flow),
                ("투자활동 CF", fs.investing_cash_flow),
                ("재무활동 CF", fs.financing_cash_flow),
                ("잉여현금흐름(FCF)", fs.free_cash_flow),
            ],
        )

    def _build_working_capital_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """운전자본 테이블 (Slide 7).

        FinancialStatements.extra 에서 'working_capital' 키를 참조한다.
        """
        fs = data.financial_statements
        wc = fs.extra.get("working_capital", {})
        if not wc:
            return [], []
        return self._rows_from_items(
            fs.years,
            [("운전자본", wc)],
        )

    def _build_capex_rows(
        self, data: IMDocumentData
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """CAPEX 테이블 (Slide 8)."""
        fs = data.financial_statements
        return self._rows_from_items(
            fs.years,
            [("CAPEX", fs.capex)],
        )

    def _build_ratio_kpis(
        self, data: IMDocumentData
    ) -> list[dict[str, str]]:
        """재무 비율 KPI 카드 (Slide 9).

        derived_metrics 에서 부채비율, ROE, ROA 등을 추출한다.
        직접 계산도 보조적으로 수행하여 데이터 가용성을 높인다.
        """
        dm = data.derived_metrics or {}
        fs = data.financial_statements
        years = fs.years
        kpis: list[dict[str, str]] = []

        # 부채비율
        if dm.get("debt_to_equity_latest") is not None:
            kpis.append({
                "label": "부채비율",
                "value": _fmt_pct(dm["debt_to_equity_latest"]),
            })
        elif years:
            latest = years[-1]
            eq = fs.total_equity.get(latest)
            liab = fs.total_liabilities.get(latest)
            if eq and eq > 0 and liab is not None:
                kpis.append({
                    "label": f"부채비율 ({latest})",
                    "value": _fmt_pct(liab / eq),
                })

        # ROE (순이익 / 자기자본)
        if years:
            latest = years[-1]
            ni = fs.net_income.get(latest)
            eq = fs.total_equity.get(latest)
            if ni is not None and eq and eq > 0:
                kpis.append({
                    "label": f"ROE ({latest})",
                    "value": _fmt_pct(ni / eq),
                })

        # ROA (순이익 / 총자산)
        if years:
            latest = years[-1]
            ni = fs.net_income.get(latest)
            ta = fs.total_assets.get(latest)
            if ni is not None and ta and ta > 0:
                kpis.append({
                    "label": f"ROA ({latest})",
                    "value": _fmt_pct(ni / ta),
                })

        # 순이익률
        if dm.get("net_margin_latest") is not None:
            kpis.append({
                "label": "순이익률",
                "value": _fmt_pct(dm["net_margin_latest"]),
            })

        # EBITDA 마진율
        if dm.get("ebitda_margin_latest") is not None:
            kpis.append({
                "label": "EBITDA 마진율",
                "value": _fmt_pct(dm["ebitda_margin_latest"]),
            })

        # 매출총이익률
        if dm.get("gross_margin_latest") is not None:
            kpis.append({
                "label": "매출총이익률",
                "value": _fmt_pct(dm["gross_margin_latest"]),
            })

        # 영업이익률
        if dm.get("operating_margin_latest") is not None:
            kpis.append({
                "label": "영업이익률",
                "value": _fmt_pct(dm["operating_margin_latest"]),
            })

        # 매출 CAGR (3Y / 5Y)
        if dm.get("revenue_cagr_3y") is not None:
            kpis.append({
                "label": "매출 CAGR (3Y)",
                "value": _fmt_pct(dm["revenue_cagr_3y"]),
            })
        if dm.get("revenue_cagr_5y") is not None:
            kpis.append({
                "label": "매출 CAGR (5Y)",
                "value": _fmt_pct(dm["revenue_cagr_5y"]),
            })

        return kpis

    def _build_revenue_yoy_bullets(
        self, data: IMDocumentData
    ) -> list[str]:
        """매출 YoY 정보를 bullet list 용 문자열로 생성 (Slide 3 fallback)."""
        fs = data.financial_statements
        years = fs.years
        bullets: list[str] = []
        for i in range(1, len(years)):
            prev_y, cur_y = years[i - 1], years[i]
            prev_v = fs.revenue.get(prev_y)
            cur_v = fs.revenue.get(cur_y)
            if prev_v is not None and cur_v is not None and prev_v != 0:
                yoy = (cur_v - prev_v) / abs(prev_v)
                bullets.append(
                    f"{cur_y} 매출: {_fmt_amount(cur_v)} "
                    f"(YoY {'+' if yoy >= 0 else ''}{yoy * 100:.1f}%)"
                )
            elif cur_v is not None:
                bullets.append(f"{cur_y} 매출: {_fmt_amount(cur_v)}")
        return bullets

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        raise NotImplementedError("PDF output removed")

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        """PPTX 슬라이드 렌더링 (최대 10개, 데이터 없으면 동적 스킵).

        슬라이드 구성:
          1. Financial KPI Dashboard
          2. P&L Summary Table
          3. Revenue Trend (차트 or bullet list)
          4. Profitability Analysis
          5. Balance Sheet Summary
          6. Cash Flow Analysis
          7. Working Capital (extra 필드)
          8. CAPEX
          9. Financial Ratio Dashboard
         10. Chart slides (기존 차트 이미지)
        """
        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_body_textbox,
            add_bullet_list,
            add_chart_or_image,
            add_financial_table,
            add_kpi_grid,
            add_sub_header_bar,
        )

        result: list[Any] = []
        fs = data.financial_statements
        dm = data.derived_metrics or {}

        # ── Slide 1: Financial KPI Dashboard ──
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

        # ── Slide 2: P&L Summary Table ──
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

        # ── Slide 3: Revenue Trend ──
        # 차트 중 "revenue" 관련이 있으면 차트, 없으면 bullet list
        chart_list = data.charts.get("financial_analysis", [])
        revenue_chart_obj = None
        remaining_charts: list[Any] = []
        for chart in chart_list:
            chart_data = chart.data
            has_img = chart_data.get("image_bytes") or chart_data.get("image_path")
            has_native_data = bool(chart.chart_type)
            title_lower = (chart.title or "").lower()
            if (has_img or has_native_data) and revenue_chart_obj is None and (
                "revenue" in title_lower
                or "매출" in title_lower
                or "revenue_yoy" in chart_data
            ):
                revenue_chart_obj = chart
            else:
                remaining_charts.append(chart)

        if revenue_chart_obj is not None:
            slide3 = factory.add_content_slide(
                title=revenue_chart_obj.title or "매출 추이"
            )
            shape = add_chart_or_image(
                slide3, revenue_chart_obj,
                top=lay.content_top, tokens=tokens,
            )
            if shape is not None:
                result.append(slide3)
        else:
            # Fallback: 매출 YoY bullet list
            bullets = self._build_revenue_yoy_bullets(data)
            if bullets:
                slide3 = factory.add_content_slide(title="매출 추이")
                add_sub_header_bar(
                    slide3, "연도별 매출 및 YoY 성장률",
                    top=lay.content_top, tokens=tokens,
                )
                add_bullet_list(
                    slide3, bullets,
                    top=lay.content_top + 0.5, tokens=tokens,
                )
                result.append(slide3)

        # ── Slide 4: Profitability Analysis ──
        prof_headers, prof_rows = self._build_profitability_rows(data)
        if prof_rows:
            slide4 = factory.add_content_slide(title="수익성 분석")
            add_sub_header_bar(
                slide4, "연도별 수익성 지표 추이",
                top=lay.content_top, tokens=tokens,
            )
            # 수익성 행의 값은 비율이므로 % 포맷 적용을 위해 직접 테이블 빌드
            # _fmt_pct 적용된 문자열 행으로 변환
            pct_rows: list[dict[str, Any]] = []
            for row in prof_rows:
                pct_row: dict[str, Any] = {"label": row["label"]}
                for y in fs.years:
                    val = row.get(y)
                    pct_row[y] = _fmt_pct(val) if val is not None else None
                pct_rows.append(pct_row)
            add_financial_table(
                slide4,
                headers=prof_headers,
                rows=pct_rows,
                top=lay.content_top + 0.45,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide4)

        # ── Slide 5: Balance Sheet Summary ──
        bs_headers, bs_rows = self._build_balance_sheet_rows(data)
        if bs_rows:
            slide5 = factory.add_content_slide(title="재무상태표 요약")
            add_financial_table(
                slide5,
                headers=bs_headers,
                rows=bs_rows,
                top=lay.content_top,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide5)

        # ── Slide 6: Cash Flow Analysis ──
        cf_headers, cf_rows = self._build_cash_flow_rows(data)
        if cf_rows:
            slide6 = factory.add_content_slide(title="현금흐름 분석")
            add_financial_table(
                slide6,
                headers=cf_headers,
                rows=cf_rows,
                top=lay.content_top,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide6)

        # ── Slide 7: Working Capital ──
        wc_headers, wc_rows = self._build_working_capital_rows(data)
        if wc_rows:
            slide7 = factory.add_content_slide(title="운전자본")
            add_financial_table(
                slide7,
                headers=wc_headers,
                rows=wc_rows,
                top=lay.content_top,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide7)

        # ── Slide 8: CAPEX ──
        capex_headers, capex_rows = self._build_capex_rows(data)
        if capex_rows:
            slide8 = factory.add_content_slide(title="CAPEX")
            add_financial_table(
                slide8,
                headers=capex_headers,
                rows=capex_rows,
                top=lay.content_top,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide8)

        # ── Slide 9: Financial Ratio Dashboard ──
        ratio_kpis = self._build_ratio_kpis(data)
        if ratio_kpis:
            slide9 = factory.add_content_slide(title="재무 비율 Dashboard")
            add_sub_header_bar(
                slide9, "주요 재무 비율",
                top=lay.content_top, tokens=tokens,
            )
            add_kpi_grid(
                slide9, ratio_kpis,
                top=lay.content_top + 0.5,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide9)

        # ── Slide 10: 나머지 차트 슬라이드 (네이티브 또는 이미지) ──
        for chart in remaining_charts:
            chart_slide = factory.add_content_slide(
                title=chart.title or "재무 차트"
            )
            shape = add_chart_or_image(
                chart_slide, chart, top=lay.content_top, tokens=tokens
            )
            if shape is not None:
                result.append(chart_slide)

        return result
