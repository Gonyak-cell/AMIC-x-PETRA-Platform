"""회사 개요(Company Overview) 섹션 렌더러.

연혁, 사업 모델, 주요 제품, 임직원 수, 본사, 인증 등 회사 기본 정보.
"""

from __future__ import annotations

import logging
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData

from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer

logger = logging.getLogger(__name__)


@register_renderer
class CompanyOverviewRenderer(BaseSectionRenderer):
    """회사 개요 슬라이드 렌더러."""

    section_id = "company_overview"

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
        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_body_textbox,
            add_bullet_list,
            add_sub_header_bar,
            add_summary_textbox,
        )

        slides: list[Any] = []
        co = data.company_overview
        narrative = data.narratives.get("company_overview", "")

        # ── Slide 1: Company Profile ──
        slide1 = factory.add_content_slide(title="회사 개요")
        y = lay.content_top

        if narrative:
            add_summary_textbox(slide1, narrative, top=y, tokens=tokens)
            y += 0.7

        if co:
            info_lines: list[str] = []
            if data.company_name_kr:
                info_lines.append(f"회사명: {data.company_name_kr}")
            if co.established_date:
                info_lines.append(f"설립일: {co.established_date}")
            if co.headquarters:
                info_lines.append(f"본사: {co.headquarters}")
            if co.employee_count is not None:
                info_lines.append(f"임직원 수: {co.employee_count:,}명")
            if info_lines:
                add_sub_header_bar(slide1, "회사 정보", top=y, tokens=tokens)
                y += 0.45
                add_body_textbox(
                    slide1, "\n".join(info_lines), top=y, height=1.2, tokens=tokens
                )
                y += 1.4

            # 사업 개요 서술 (business_description)
            if co.business_description:
                add_sub_header_bar(slide1, "사업 개요", top=y, tokens=tokens)
                y += 0.45
                add_body_textbox(
                    slide1,
                    co.business_description,
                    top=y,
                    height=1.8,
                    tokens=tokens,
                )

        slides.append(slide1)

        if not co:
            return slides

        # ── Slide 2: History Timeline ──
        if co.history:
            slide2 = factory.add_content_slide(title="연혁")
            y = lay.content_top

            add_sub_header_bar(slide2, "회사 연혁", top=y, tokens=tokens)
            y += 0.45

            timeline_lines: list[str] = []
            for entry in co.history:
                year = entry.get("year", "")
                event = entry.get("event", "")
                if year or event:
                    timeline_lines.append(f"{year}  {event}")

            if timeline_lines:
                add_body_textbox(
                    slide2,
                    "\n".join(timeline_lines),
                    top=y,
                    height=min(len(timeline_lines) * 0.35, 5.5),
                    tokens=tokens,
                )

            slides.append(slide2)

        # ── Slide 3: Products & Services ──
        if co.key_products:
            slide3 = factory.add_content_slide(title="주요 제품/서비스")
            y = lay.content_top

            add_sub_header_bar(
                slide3, "주요 제품/서비스", top=y, tokens=tokens
            )
            y += 0.45

            # 번호 매기기 (numbered bullet list)
            numbered_items = [
                f"{i}. {product}"
                for i, product in enumerate(co.key_products, start=1)
            ]
            add_body_textbox(
                slide3,
                "\n".join(numbered_items),
                top=y,
                height=min(len(numbered_items) * 0.35, 5.5),
                tokens=tokens,
            )

            slides.append(slide3)

        # ── Slide 4: Certifications & Awards ──
        if co.certifications:
            slide4 = factory.add_content_slide(title="인증 및 수상")
            y = lay.content_top

            add_sub_header_bar(slide4, "인증 및 수상", top=y, tokens=tokens)
            y += 0.45

            add_bullet_list(
                slide4,
                co.certifications,
                top=y,
                height=min(len(co.certifications) * 0.35, 5.5),
                tokens=tokens,
            )

            slides.append(slide4)

        # ── Slide 5: Geographic Presence ──
        has_locations = co.headquarters or co.locations
        if has_locations:
            slide5 = factory.add_content_slide(title="사업장 현황")
            y = lay.content_top

            add_sub_header_bar(slide5, "사업장 현황", top=y, tokens=tokens)
            y += 0.45

            geo_lines: list[str] = []
            if co.headquarters:
                geo_lines.append(f"본사: {co.headquarters}")
            for loc in co.locations:
                geo_lines.append(f"사업장: {loc}")

            if geo_lines:
                add_body_textbox(
                    slide5,
                    "\n".join(geo_lines),
                    top=y,
                    height=min(len(geo_lines) * 0.4, 4.0),
                    tokens=tokens,
                )

            slides.append(slide5)

        # ── Slide 6 (optional): Organization ──
        has_org = co.organization or co.departments
        if has_org:
            slide6 = factory.add_content_slide(title="조직 구조")
            y = lay.content_top

            add_sub_header_bar(slide6, "조직 구조", top=y, tokens=tokens)
            y += 0.45

            if co.departments:
                dept_lines: list[str] = []
                for dept in co.departments:
                    name = dept.get("name", "")
                    head = dept.get("head", "")
                    headcount = dept.get("headcount", "")
                    parts = [name]
                    if head:
                        parts.append(f"책임자: {head}")
                    if headcount:
                        parts.append(f"인원: {headcount}")
                    dept_lines.append(" | ".join(parts))
                add_body_textbox(
                    slide6,
                    "\n".join(dept_lines),
                    top=y,
                    height=min(len(dept_lines) * 0.35, 5.0),
                    tokens=tokens,
                )
            elif co.organization:
                add_bullet_list(
                    slide6,
                    co.organization,
                    top=y,
                    height=min(len(co.organization) * 0.35, 5.0),
                    tokens=tokens,
                )

            slides.append(slide6)

        return slides
