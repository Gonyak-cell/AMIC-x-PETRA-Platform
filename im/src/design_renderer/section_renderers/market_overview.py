"""시장 분석(Market Overview) 섹션 렌더러.

TAM/SAM/SOM, 시장 성장률, 경쟁사 현황, 산업 트렌드를 표시.
"""

from __future__ import annotations

import logging
from html import escape as html_escape
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData

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
        raise NotImplementedError("PDF output removed")

    def _build_competitor_table(
        self, md: Any
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """경쟁사 테이블 headers + rows 생성."""
        headers = ["기업명", "매출액 (억원)", "시장 점유율"]
        rows: list[dict[str, Any]] = []
        for comp in md.competitors:
            name = comp.get("name", "")
            rev = comp.get("revenue")
            ms = comp.get("market_share")
            rows.append({
                "label": name,
                "매출액 (억원)": f"{rev:,.0f}" if rev is not None else "N/A",
                "시장 점유율": f"{ms * 100:.1f}%" if ms is not None else "N/A",
            })
        return headers, rows

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
            add_chart_or_image,
            add_financial_table,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
        )

        result: list[Any] = []
        md = data.market_data
        narrative = data.narratives.get("market_overview", "")
        kpis = self._build_market_kpis(data)

        # ------------------------------------------------------------------
        # Slide 1: Market Size KPI Dashboard
        # ------------------------------------------------------------------
        if kpis:
            slide1 = factory.add_content_slide(title="시장 분석")
            y = lay.content_top
            add_kpi_grid(
                slide1,
                kpis,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 1.6

            # 시장 포지셔닝 요약이 있으면 KPI 아래에 추가
            if md and md.market_position:
                add_summary_textbox(
                    slide1, md.market_position, top=y, tokens=tokens
                )
            result.append(slide1)

        # ------------------------------------------------------------------
        # Slide 2: Market Narrative (AI 내러티브 전문)
        # ------------------------------------------------------------------
        if narrative:
            slide2 = factory.add_content_slide(title="시장 분석 상세")
            add_body_textbox(
                slide2, narrative, top=lay.content_top, height=5.0, tokens=tokens
            )
            result.append(slide2)

        # ------------------------------------------------------------------
        # Slide 3: Competitive Landscape (경쟁사 테이블)
        # ------------------------------------------------------------------
        if md and md.competitors:
            slide3 = factory.add_content_slide(title="경쟁 환경")
            y = lay.content_top

            headers, rows = self._build_competitor_table(md)
            add_financial_table(
                slide3,
                headers=headers,
                rows=rows,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 0.5 + len(rows) * 0.35  # 테이블 높이 추정

            # 경쟁 우위 요소가 있으면 테이블 아래에 추가
            if md.competitive_advantages:
                add_sub_header_bar(
                    slide3, "경쟁 우위", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide3,
                    md.competitive_advantages,
                    top=y,
                    height=2.0,
                    tokens=tokens,
                )
            result.append(slide3)

        # ------------------------------------------------------------------
        # Slide 4: Industry Trends (산업 트렌드)
        # ------------------------------------------------------------------
        if md and md.industry_trends:
            slide4 = factory.add_content_slide(title="산업 트렌드")
            y = lay.content_top
            add_bullet_list(
                slide4,
                md.industry_trends,
                top=y,
                height=4.5,
                tokens=tokens,
            )
            result.append(slide4)

        # ------------------------------------------------------------------
        # Slide 5: Regulatory Environment (규제 환경)
        # ------------------------------------------------------------------
        if md and md.regulatory_notes:
            slide5 = factory.add_content_slide(title="규제 환경")
            y = lay.content_top
            add_sub_header_bar(
                slide5, "주요 규제 사항", top=y, tokens=tokens
            )
            y += 0.45
            add_body_textbox(
                slide5,
                md.regulatory_notes,
                top=y,
                height=4.5,
                tokens=tokens,
            )
            result.append(slide5)

        # ------------------------------------------------------------------
        # Slide 6: Market Charts (네이티브 또는 이미지)
        # ------------------------------------------------------------------
        chart_list = data.charts.get("market_overview", [])
        for chart in chart_list:
            chart_slide = factory.add_content_slide(
                title=chart.title or "시장 분석 차트"
            )
            shape = add_chart_or_image(
                chart_slide, chart, top=lay.content_top, tokens=tokens
            )
            if shape is not None:
                result.append(chart_slide)

        # 데이터가 전혀 없는 경우 빈 슬라이드 1개라도 반환
        if not result:
            fallback = factory.add_content_slide(title="시장 분석")
            add_body_textbox(
                fallback,
                "시장 분석 데이터가 준비되지 않았습니다.",
                top=lay.content_top,
                tokens=tokens,
            )
            result.append(fallback)

        return result
