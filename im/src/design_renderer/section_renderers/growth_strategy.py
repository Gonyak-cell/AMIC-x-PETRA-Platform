"""성장 전략(Growth Strategy) 섹션 렌더러.

슬라이드 구성 (최대 5개, 데이터 없으면 동적 스킵):
  1. Growth Strategy Overview — AI 내러티브 + 전략 카테고리 요약
  2. Organic Growth — organic_growth 불릿 리스트
  3. New Business / M&A — new_business + ma_targets 결합
  4. Roadmap Timeline — roadmap 연도별 타임라인
  5. Charts — 차트 이미지 삽입
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
class GrowthStrategyRenderer(BaseSectionRenderer):
    """성장 전략 슬라이드 렌더러."""

    section_id = "growth_strategy"

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
        """성장 전략 다중 슬라이드 렌더러.

        슬라이드 구성 (최대 5개, 데이터 없으면 동적 스킵):
          1. Growth Strategy Overview — AI 내러티브 + 전략 카테고리 요약
          2. Organic Growth — organic_growth 불릿 리스트 (데이터 있을 때만)
          3. New Business / M&A — new_business + ma_targets (데이터 있을 때만)
          4. Roadmap Timeline — roadmap 연도별 타임라인 (데이터 있을 때만)
          5. Charts — 차트 이미지 (데이터 있을 때만)
        """
        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_bullet_list,
            add_chart_or_image,
            add_sub_header_bar,
            add_summary_textbox,
        )

        result: list[Any] = []
        gs = data.growth_strategy
        narrative = data.narratives.get("growth_strategy", "")

        # ── 슬라이드 1: Growth Strategy Overview ──
        slide1 = factory.add_content_slide(title="성장 전략")
        y = lay.content_top

        if narrative:
            add_summary_textbox(slide1, narrative, top=y, tokens=tokens)
            y += 0.7

        # 전략 카테고리 요약 (각 카테고리 존재 여부 + 첫 번째 항목 미리보기)
        if gs:
            summary_lines: list[str] = []
            if gs.organic_growth:
                preview = gs.organic_growth[0]
                suffix = (
                    f" 외 {len(gs.organic_growth) - 1}건"
                    if len(gs.organic_growth) > 1
                    else ""
                )
                summary_lines.append(f"유기적 성장: {preview}{suffix}")
            if gs.new_business:
                preview = gs.new_business[0]
                suffix = (
                    f" 외 {len(gs.new_business) - 1}건"
                    if len(gs.new_business) > 1
                    else ""
                )
                summary_lines.append(f"신규 사업: {preview}{suffix}")
            if gs.ma_targets:
                preview = gs.ma_targets[0]
                suffix = (
                    f" 외 {len(gs.ma_targets) - 1}건"
                    if len(gs.ma_targets) > 1
                    else ""
                )
                summary_lines.append(f"M&A 전략: {preview}{suffix}")
            if gs.roadmap:
                years = sorted(gs.roadmap.keys())
                summary_lines.append(
                    f"로드맵: {years[0]}~{years[-1]} ({len(years)}개년)"
                    if len(years) > 1
                    else f"로드맵: {years[0]}"
                )

            if summary_lines:
                add_sub_header_bar(
                    slide1, "전략 개요", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide1,
                    summary_lines,
                    top=y,
                    height=1.0 + 0.25 * max(0, len(summary_lines) - 3),
                    tokens=tokens,
                )

        result.append(slide1)

        # ── 슬라이드 2: Organic Growth ──
        if gs and gs.organic_growth:
            slide2 = factory.add_content_slide(title="유기적 성장 전략")
            y2 = lay.content_top
            add_sub_header_bar(
                slide2, "유기적 성장", top=y2, tokens=tokens
            )
            y2 += 0.45
            add_bullet_list(
                slide2,
                gs.organic_growth,
                top=y2,
                height=2.5 + 0.3 * max(0, len(gs.organic_growth) - 5),
                tokens=tokens,
            )
            result.append(slide2)

        # ── 슬라이드 3: New Business / M&A ──
        has_new_biz = gs and gs.new_business
        has_ma = gs and gs.ma_targets
        if has_new_biz or has_ma:
            slide3 = factory.add_content_slide(
                title="신규 사업 및 M&A 전략"
            )
            y3 = lay.content_top

            if has_new_biz:
                add_sub_header_bar(
                    slide3, "신규 사업", top=y3, tokens=tokens
                )
                y3 += 0.45
                add_bullet_list(
                    slide3,
                    gs.new_business,
                    top=y3,
                    height=1.0 + 0.25 * max(0, len(gs.new_business) - 3),
                    tokens=tokens,
                )
                y3 += 1.2 + 0.25 * max(0, len(gs.new_business) - 3)

            if has_ma:
                add_sub_header_bar(
                    slide3, "M&A 전략", top=y3, tokens=tokens
                )
                y3 += 0.45
                add_bullet_list(
                    slide3,
                    gs.ma_targets,
                    top=y3,
                    height=1.0 + 0.25 * max(0, len(gs.ma_targets) - 3),
                    tokens=tokens,
                )

            result.append(slide3)

        # ── 슬라이드 4: Roadmap Timeline ──
        if gs and gs.roadmap:
            slide4 = factory.add_content_slide(title="성장 로드맵")
            y4 = lay.content_top
            add_sub_header_bar(slide4, "로드맵", top=y4, tokens=tokens)
            y4 += 0.45

            for year, goals in sorted(gs.roadmap.items()):
                # 연도를 서브 헤더로, 목표를 불릿으로 표시
                add_sub_header_bar(
                    slide4, f"{year}년 목표", top=y4, tokens=tokens
                )
                y4 += 0.4
                add_bullet_list(
                    slide4,
                    goals,
                    top=y4,
                    height=0.3 * len(goals) + 0.2,
                    tokens=tokens,
                )
                y4 += 0.3 * len(goals) + 0.35

            result.append(slide4)

        # ── 슬라이드 5: Charts (네이티브 또는 이미지) ──
        chart_list = data.charts.get("growth_strategy", [])
        for chart in chart_list:
            chart_slide = factory.add_content_slide(
                title=chart.title or "성장 전략 차트"
            )
            shape = add_chart_or_image(
                chart_slide, chart, top=lay.content_top, tokens=tokens
            )
            if shape is not None:
                result.append(chart_slide)

        return result
