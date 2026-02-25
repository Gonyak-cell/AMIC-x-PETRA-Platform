"""TM 전용 별칭 렌더러 — 기존 렌더러를 타이틀만 변경하여 재사용.

target_overview → company_overview 기반 (타이틀: "Target Overview")
target_highlights → business_overview 기반 (타이틀: "Target Highlights")
"""

from __future__ import annotations

import logging
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData
from src.design_renderer.pdf_output.html_builder import build_slide_html
from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer

logger = logging.getLogger(__name__)


@register_renderer
class TargetOverviewRenderer(BaseSectionRenderer):
    """Target Overview 슬라이드 렌더러 (company_overview 기반)."""

    section_id = "target_overview"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        from src.design_renderer.section_renderers.company_overview import (
            CompanyOverviewRenderer,
        )

        # TM 프롬프트가 "target_overview" 키로 생성한 내러티브를
        # company_overview 키에도 복사 (delegate가 읽을 수 있도록)
        if "target_overview" in data.narratives and "company_overview" not in data.narratives:
            data.narratives["company_overview"] = data.narratives["target_overview"]

        delegate = CompanyOverviewRenderer()
        slides = delegate.render_html(data, tokens=tokens)

        # 타이틀 치환: "회사 개요" → "Target Overview"
        return [
            s.replace(">회사 개요<", ">Target Overview<")
            for s in slides
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
            add_bullet_list,
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Target Overview")
        co = data.company_overview
        # TM 프롬프트는 "target_overview" 키로 내러티브 생성, 폴백으로 "company_overview"
        narrative = data.narratives.get("target_overview", "") or data.narratives.get("company_overview", "")

        y = lay.content_top

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        if co:
            info_lines = []
            if data.company_name_kr:
                info_lines.append(f"회사명: {data.company_name_kr}")
            if co.established_date:
                info_lines.append(f"설립일: {co.established_date}")
            if co.headquarters:
                info_lines.append(f"본사: {co.headquarters}")
            if co.employee_count is not None:
                info_lines.append(f"임직원 수: {co.employee_count:,}명")
            if info_lines:
                add_sub_header_bar(slide, "회사 정보", top=y, tokens=tokens)
                y += 0.45
                add_body_textbox(
                    slide, "\n".join(info_lines), top=y, height=1.2,
                    tokens=tokens,
                )
                y += 1.4

            if co.key_products:
                add_sub_header_bar(
                    slide, "주요 제품/서비스", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide, co.key_products, top=y, height=1.5, tokens=tokens
                )

        return [slide]


@register_renderer
class TargetHighlightsRenderer(BaseSectionRenderer):
    """Target Highlights 슬라이드 렌더러 (business_overview 기반)."""

    section_id = "target_highlights"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        from src.design_renderer.section_renderers.business_overview import (
            BusinessOverviewRenderer,
        )

        # TM 프롬프트가 "target_highlights" 키로 생성한 내러티브를
        # business_overview 키에도 복사 (delegate가 읽을 수 있도록)
        if "target_highlights" in data.narratives and "business_overview" not in data.narratives:
            data.narratives["business_overview"] = data.narratives["target_highlights"]

        delegate = BusinessOverviewRenderer()
        slides = delegate.render_html(data, tokens=tokens)

        # 타이틀 치환: "사업 개요" → "Target Highlights"
        return [
            s.replace(">사업 개요<", ">Target Highlights<")
            for s in slides
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
            add_bullet_list,
            add_financial_table,
            add_sub_header_bar,
            add_summary_textbox,
            shape_bottom_inches,
        )

        slide = factory.add_content_slide(title="Target Highlights")
        # TM 프롬프트는 "target_highlights" 키로 내러티브 생성, 폴백으로 "business_overview"
        narrative = data.narratives.get("target_highlights", "") or data.narratives.get("business_overview", "")

        y = lay.content_top

        if narrative:
            shape = add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y = shape_bottom_inches(shape) + 0.1

        # 사업부별 매출 테이블
        if data.segment_revenue and data.segment_revenue.segments:
            segments = data.segment_revenue.segments
            all_years: set[str] = set()
            for yearly in segments.values():
                all_years.update(yearly.keys())
            years = sorted(all_years)

            headers = ["사업부"] + years
            rows = []
            for seg_name, yearly in segments.items():
                row: dict[str, Any] = {"label": seg_name}
                for y_str in years:
                    row[y_str] = yearly.get(y_str)
                rows.append(row)

            add_sub_header_bar(slide, "사업부별 매출", top=y, tokens=tokens)
            y += 0.45
            add_financial_table(
                slide,
                headers=headers,
                rows=rows,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 2.5

        # 주요 고객
        if data.key_customers:
            add_sub_header_bar(slide, "주요 고객", top=y, tokens=tokens)
            y += 0.45
            add_bullet_list(
                slide, data.key_customers, top=y, height=1.5, tokens=tokens
            )

        return [slide]
