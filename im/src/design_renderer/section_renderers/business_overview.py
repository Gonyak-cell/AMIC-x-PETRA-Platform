"""사업 개요(Business Overview) 섹션 렌더러.

사업부별 매출 구성, 주요 고객, 사업 설명 등 사업 현황 정보.

PPTX 슬라이드 구성 (최대 6개, 데이터 없으면 동적 스킵):
  1. Business Overview Narrative — AI narrative 요약 + 사업 개요
  2. Segment Revenue Table — 사업부별 매출 테이블
  3. Segment Deep Dive — 세그먼트별 매출 비중/성장률 KPI 카드
  4. Key Customers — 주요 고객 bullet list + customer concentration
  5. Operational Efficiency — 운영 효율성 지표 (industry_data 기반)
  6. Charts — 차트 이미지
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
class BusinessOverviewRenderer(BaseSectionRenderer):
    """사업 개요 슬라이드 렌더러."""

    section_id = "business_overview"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        raise NotImplementedError("PDF output removed")

    # ------------------------------------------------------------------
    # Internal helpers for segment data
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_segment_years(
        segments: dict[str, dict[str, float | None]],
    ) -> list[str]:
        """세그먼트 데이터에서 연도 목록 추출 (정렬)."""
        all_years: set[str] = set()
        for yearly in segments.values():
            all_years.update(yearly.keys())
        return sorted(all_years)

    @staticmethod
    def _build_segment_table(
        segments: dict[str, dict[str, float | None]],
        years: list[str],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """세그먼트 데이터를 financial_table 형식으로 변환."""
        headers = ["사업부"] + years
        rows: list[dict[str, Any]] = []
        for seg_name, yearly in segments.items():
            row: dict[str, Any] = {"label": seg_name}
            for y_str in years:
                row[y_str] = yearly.get(y_str)
            rows.append(row)
        return headers, rows

    @staticmethod
    def _build_segment_kpis(
        segments: dict[str, dict[str, float | None]],
        years: list[str],
    ) -> list[dict[str, str]]:
        """세그먼트별 매출 비중 + 성장률 KPI 카드 데이터 생성."""
        kpis: list[dict[str, str]] = []
        if not years:
            return kpis

        latest = years[-1]

        # 최신 연도 총 매출 계산
        total_latest: float = 0.0
        for yearly in segments.values():
            val = yearly.get(latest)
            if val is not None:
                total_latest += val

        for seg_name, yearly in segments.items():
            latest_val = yearly.get(latest)
            if latest_val is None:
                continue

            # 매출 비중
            share = latest_val / total_latest if total_latest > 0 else 0.0
            label_parts = [f"{seg_name} ({latest})"]
            value_parts = [f"{_fmt_pct(share)} 비중"]

            # YoY 성장률 (연도 2개 이상일 때)
            if len(years) >= 2:
                prev = years[-2]
                prev_val = yearly.get(prev)
                if prev_val is not None and prev_val != 0:
                    yoy = (latest_val - prev_val) / abs(prev_val)
                    value_parts.append(f"YoY {_fmt_pct(yoy)}")

            kpis.append({
                "label": label_parts[0],
                "value": " | ".join(value_parts),
            })

        return kpis

    # ------------------------------------------------------------------
    # PPTX rendering — multi-slide
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
            add_bullet_list,
            add_chart_image,
            add_financial_table,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
        )

        result: list[Any] = []

        narrative = data.narratives.get("business_overview", "")
        has_segments = bool(
            data.segment_revenue and data.segment_revenue.segments
        )
        segments = (
            data.segment_revenue.segments if has_segments else {}
        )
        years = self._extract_segment_years(segments) if has_segments else []

        # ── Slide 1: Business Overview Narrative ──
        if narrative:
            slide1 = factory.add_content_slide(title="사업 개요")
            y = lay.content_top
            add_summary_textbox(slide1, narrative, top=y, tokens=tokens)
            y += 0.7

            # 간략한 사업 개요 보조 텍스트 (company_overview.business_description)
            biz_desc = ""
            if data.company_overview:
                biz_desc = data.company_overview.business_description
            if biz_desc:
                add_body_textbox(slide1, biz_desc, top=y, tokens=tokens)

            result.append(slide1)

        # ── Slide 2: Segment Revenue Table ──
        if has_segments:
            slide2 = factory.add_content_slide(title="사업부별 매출")
            y = lay.content_top

            headers, rows = self._build_segment_table(segments, years)
            add_financial_table(
                slide2,
                headers=headers,
                rows=rows,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide2)

        # ── Slide 3: Segment Deep Dive (KPI Cards) ──
        if has_segments and len(segments) >= 2:
            seg_kpis = self._build_segment_kpis(segments, years)
            if seg_kpis:
                slide3 = factory.add_content_slide(
                    title="세그먼트별 매출 분석"
                )
                y = lay.content_top
                cols = min(len(seg_kpis), 4)
                add_kpi_grid(
                    slide3,
                    seg_kpis,
                    top=y,
                    cols=cols,
                    tokens=tokens,
                    number_config=data.number_format,
                )
                result.append(slide3)

        # ── Slide 4: Key Customers ──
        if data.key_customers:
            slide4 = factory.add_content_slide(title="주요 고객")
            y = lay.content_top

            # Customer concentration 정보 (상위 고객 수 표시)
            n_customers = len(data.key_customers)
            concentration_text = (
                f"총 {n_customers}개 주요 고객사"
            )
            add_sub_header_bar(
                slide4, concentration_text, top=y, tokens=tokens
            )
            y += 0.45

            add_bullet_list(
                slide4,
                data.key_customers,
                top=y,
                height=min(n_customers * 0.35, 4.5),
                tokens=tokens,
            )
            result.append(slide4)

        # ── Slide 5: Operational Efficiency ──
        # industry_data에 운영 효율성 관련 지표가 있으면 KPI 카드로 표시
        ops_kpis = self._build_ops_efficiency_kpis(data)
        if ops_kpis:
            slide5 = factory.add_content_slide(title="운영 효율성")
            y = lay.content_top
            cols = min(len(ops_kpis), 4)
            add_kpi_grid(
                slide5,
                ops_kpis,
                top=y,
                cols=cols,
                tokens=tokens,
                number_config=data.number_format,
            )
            result.append(slide5)

        # ── Slide 6: Charts ──
        chart_list = data.charts.get("business_overview", [])
        for chart in chart_list:
            chart_data = chart.data
            img = chart_data.get("image_bytes") or chart_data.get(
                "image_path"
            )
            if img:
                chart_slide = factory.add_content_slide(
                    title=chart.title or "사업 개요 차트"
                )
                add_chart_image(
                    chart_slide, img, top=lay.content_top, tokens=tokens
                )
                result.append(chart_slide)

        # 데이터가 전혀 없는 극단적 경우 — 빈 슬라이드 1개라도 반환
        if not result:
            fallback = factory.add_content_slide(title="사업 개요")
            add_body_textbox(
                fallback,
                "사업 개요 데이터가 준비되지 않았습니다.",
                top=lay.content_top,
                tokens=tokens,
            )
            result.append(fallback)

        return result

    @staticmethod
    def _build_ops_efficiency_kpis(
        data: IMDocumentData,
    ) -> list[dict[str, str]]:
        """industry_data + derived_metrics에서 운영 효율성 KPI 추출."""
        kpis: list[dict[str, str]] = []
        ind = data.industry_data or {}
        dm = data.derived_metrics or {}
        fs = data.financial_statements

        # industry_data 기반 운영 지표
        ops_fields = [
            ("employee_productivity", "1인당 생산성"),
            ("utilization_rate", "가동률"),
            ("inventory_turnover", "재고 회전율"),
            ("receivable_days", "매출채권 회수일"),
            ("asset_turnover", "자산 회전율"),
            ("capacity_utilization", "설비 가동률"),
        ]
        for key, label in ops_fields:
            val = ind.get(key)
            if val is not None:
                if isinstance(val, float) and val < 10:
                    # 비율(0~1 범위)이면 퍼센트 표시
                    kpis.append({"label": label, "value": _fmt_pct(val)})
                else:
                    kpis.append({"label": label, "value": _fmt_amount(val)})

        # derived_metrics에서 마진율 지표 (아직 KPI 슬라이드에 없는 것)
        margin_fields = [
            ("gross_margin_latest", "매출총이익률"),
            ("operating_margin_latest", "영업이익률"),
            ("ebitda_margin_latest", "EBITDA 마진율"),
        ]
        for key, label in margin_fields:
            val = dm.get(key)
            if val is not None:
                kpis.append({"label": label, "value": _fmt_pct(val)})

        # 판관비 비율 (SGA/매출)
        years = fs.years
        if years:
            latest = years[-1]
            rev = fs.revenue.get(latest)
            sga = fs.sga_expenses.get(latest)
            if rev and sga and rev > 0:
                sga_ratio = sga / rev
                kpis.append({
                    "label": f"판관비율 ({latest})",
                    "value": _fmt_pct(sga_ratio),
                })

        return kpis
