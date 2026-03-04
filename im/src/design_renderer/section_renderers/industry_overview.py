"""산업 개요 + 운영 분석 섹션 렌더러 (A2).

> 마지막 수정: 2026-02-11 14:00:00

산업 개요 내러티브, 강조 영역, 운영 분석 차트,
리스크 카테고리를 산업별 레이아웃으로 렌더링한다.
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
class IndustryOverviewRenderer(BaseSectionRenderer):
    """산업 개요 + 운영 분석 렌더러.

    Slide 1: 산업 개요 내러티브 + 강조 영역 (bullet list).
    Slide 2 (조건부): 운영 분석 차트 + 리스크 테이블.
    """

    section_id = "industry_overview"

    def _get_module(self, data: IMDocumentData) -> Any | None:
        """산업 모듈을 조회한다."""
        if not data.industry:
            return None
        try:
            from src.industry.registry import get_industry_module_safe

            return get_industry_module_safe(data.industry)
        except Exception:
            logger.warning("산업 모듈 조회 실패: %s", data.industry, exc_info=True)
            return None

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        """산업 개요 HTML 슬라이드를 반환한다."""
        module = self._get_module(data)
        if module is None:
            return []

        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors
        slides: list[str] = []

        # ── Slide 1: 산업 개요 내러티브 + 강조 영역 ──
        narrative = html_escape(data.narratives.get("industry_overview", ""))
        variant = module.get_narrative_variant()
        emphasis_areas = variant.get_emphasis_areas() if variant else []

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.7;margin-bottom:1em;">{narrative}</p>'
            )

        emphasis_html = ""
        if emphasis_areas:
            items = "".join(
                f'<li style="font-size:9pt;color:{c.text_body};'
                f'margin-bottom:0.3em;">{html_escape(area)}</li>'
                for area in emphasis_areas
            )
            emphasis_html = (
                f'<div style="margin-top:0.8em;">'
                f'<div style="font-size:10pt;font-weight:bold;'
                f'color:{c.primary};margin-bottom:0.4em;">핵심 분석 영역</div>'
                f'<ul style="padding-left:1.2em;">{items}</ul></div>'
            )

        title = f"{module.industry_name_kr} 산업 개요"
        content_1 = f"{narrative_html}{emphasis_html}"
        slides.append(
            build_slide_html(
                content_1,
                title=title,
                slide_class="slide-industry-overview",
                tokens=tokens,
            )
        )

        # ── Slide 2 (조건부): 차트 + 리스크 ──
        chart_list = (data.charts or {}).get("industry_overview", [])
        risk_categories = module.get_risk_categories()

        if chart_list or risk_categories:
            chart_html = ""
            for chart in chart_list:
                img_data = getattr(chart, "data", {}) or {}
                img_path = img_data.get("image_path", "")
                if img_path:
                    chart_html += (
                        f'<div style="text-align:center;margin-bottom:1em;">'
                        f'<img src="{html_escape(str(img_path))}" '
                        f'style="max-width:100%;"/></div>'
                    )

            risk_html = ""
            if risk_categories:
                rows = ""
                for rc in risk_categories:
                    factors = ", ".join(rc.risk_factors) if rc.risk_factors else "-"
                    rows += (
                        f"<tr>"
                        f'<td style="padding:4px 8px;font-weight:bold;'
                        f'font-size:9pt;">{html_escape(rc.name_kr)}</td>'
                        f'<td style="padding:4px 8px;font-size:9pt;">'
                        f"{html_escape(rc.description)}</td>"
                        f'<td style="padding:4px 8px;font-size:8pt;'
                        f'color:{c.text_secondary};">'
                        f"{html_escape(factors)}</td>"
                        f"</tr>"
                    )
                risk_html = (
                    f'<div style="margin-top:1em;">'
                    f'<div style="font-size:10pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.4em;">주요 리스크</div>'
                    f'<table style="width:100%;border-collapse:collapse;'
                    f'border:1px solid {c.bg_cool_grey};">'
                    f"<thead><tr>"
                    f'<th style="padding:6px 8px;background:{c.bg_cool_grey};'
                    f'font-size:9pt;text-align:left;">카테고리</th>'
                    f'<th style="padding:6px 8px;background:{c.bg_cool_grey};'
                    f'font-size:9pt;text-align:left;">설명</th>'
                    f'<th style="padding:6px 8px;background:{c.bg_cool_grey};'
                    f'font-size:9pt;text-align:left;">리스크 요인</th>'
                    f"</tr></thead>"
                    f"<tbody>{rows}</tbody></table></div>"
                )

            content_2 = f"{chart_html}{risk_html}"
            slides.append(
                build_slide_html(
                    content_2,
                    title=f"{module.industry_name_kr} 운영 분석",
                    slide_class="slide-industry-overview-ops",
                    tokens=tokens,
                )
            )

        return slides

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        """산업 개요 PPTX 슬라이드를 반환한다."""
        module = self._get_module(data)
        if module is None:
            return []

        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_body_textbox,
            add_bullet_list,
            add_chart_or_image,
            add_financial_table,
        )

        result: list[Any] = []

        # ── Slide 1: 내러티브 + 강조 영역 ──
        title = f"{module.industry_name_kr} 산업 개요"
        slide1 = factory.add_content_slide(title=title)
        narrative = data.narratives.get("industry_overview", "")
        variant = module.get_narrative_variant()
        emphasis_areas = variant.get_emphasis_areas() if variant else []

        y = lay.content_top

        if narrative:
            add_body_textbox(slide1, narrative, top=y, tokens=tokens)
            y += 2.0

        if emphasis_areas:
            add_bullet_list(slide1, emphasis_areas, top=y, tokens=tokens)

        result.append(slide1)

        # ── Slide 2 (조건부): 차트 + 리스크 ──
        chart_list = (data.charts or {}).get("industry_overview", [])
        risk_categories = module.get_risk_categories()

        if chart_list or risk_categories:
            slide2 = factory.add_content_slide(
                title=f"{module.industry_name_kr} 운영 분석",
            )
            y2 = lay.content_top

            for chart in chart_list:
                add_chart_or_image(slide2, chart, top=y2, tokens=tokens)
                y2 += 2.5

            if risk_categories:
                headers = ["카테고리", "설명", "리스크 요인"]
                rows = []
                for rc in risk_categories:
                    factors = ", ".join(rc.risk_factors) if rc.risk_factors else "-"
                    rows.append([rc.name_kr, rc.description, factors])
                add_financial_table(
                    slide2,
                    headers=headers,
                    rows=rows,
                    top=y2,
                    tokens=tokens,
                )

            result.append(slide2)

        return result
