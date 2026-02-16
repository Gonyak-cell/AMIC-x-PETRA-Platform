"""성장 전략(Growth Strategy) 섹션 렌더러.

유기적 성장, 신규 사업, M&A, 로드맵을 카테고리별로 표시.
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
class GrowthStrategyRenderer(BaseSectionRenderer):
    """성장 전략 슬라이드 렌더러."""

    section_id = "growth_strategy"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        gs = data.growth_strategy
        narrative = html_escape(data.narratives.get("growth_strategy", ""))

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;margin-bottom:1em;">{narrative}</p>'
            )

        strategy_html = ""
        if gs:
            sections = []

            if gs.organic_growth:
                items = "".join(
                    f'<li style="font-size:10pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">{html_escape(item)}</li>'
                    for item in gs.organic_growth
                )
                sections.append(
                    f'<div style="margin-bottom:0.8em;">'
                    f'<div style="padding:4px 10px;background:{c.primary};'
                    f'color:{c.text_white};font-weight:bold;font-size:10pt;'
                    f'border-radius:2px;margin-bottom:0.4em;">'
                    f"유기적 성장</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
                    f"</div>"
                )

            if gs.new_business:
                items = "".join(
                    f'<li style="font-size:10pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">{html_escape(item)}</li>'
                    for item in gs.new_business
                )
                sections.append(
                    f'<div style="margin-bottom:0.8em;">'
                    f'<div style="padding:4px 10px;background:{c.primary};'
                    f'color:{c.text_white};font-weight:bold;font-size:10pt;'
                    f'border-radius:2px;margin-bottom:0.4em;">'
                    f"신규 사업</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
                    f"</div>"
                )

            if gs.ma_targets:
                items = "".join(
                    f'<li style="font-size:10pt;color:{c.text_body};'
                    f'margin-bottom:0.3em;">{html_escape(item)}</li>'
                    for item in gs.ma_targets
                )
                sections.append(
                    f'<div style="margin-bottom:0.8em;">'
                    f'<div style="padding:4px 10px;background:{c.primary};'
                    f'color:{c.text_white};font-weight:bold;font-size:10pt;'
                    f'border-radius:2px;margin-bottom:0.4em;">'
                    f"M&amp;A 전략</div>"
                    f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
                    f"</div>"
                )

            # 로드맵
            if gs.roadmap:
                roadmap_items = ""
                for year, goals in sorted(gs.roadmap.items()):
                    goal_list = ", ".join(html_escape(g) for g in goals)
                    roadmap_items += (
                        f'<div style="display:flex;margin-bottom:0.4em;">'
                        f'<span style="font-weight:bold;color:{c.accent};'
                        f'min-width:50px;font-size:10pt;">'
                        f"{html_escape(year)}</span>"
                        f'<span style="color:{c.text_body};font-size:10pt;">'
                        f"{goal_list}</span></div>"
                    )
                sections.append(
                    f'<div style="margin-top:0.8em;padding:0.8em;'
                    f'background:{c.bg_cool_grey};border-radius:4px;">'
                    f'<div style="font-size:11pt;font-weight:bold;'
                    f'color:{c.primary};margin-bottom:0.4em;">로드맵</div>'
                    f"{roadmap_items}</div>"
                )

            strategy_html = "".join(sections)

        content = f"""
        {narrative_html}
        {strategy_html}
        """

        slide = build_slide_html(
            content,
            title="성장 전략",
            slide_class="slide-growth-strategy",
            tokens=tokens,
        )
        return [slide]

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

        slide = factory.add_content_slide(title="성장 전략")
        gs = data.growth_strategy
        narrative = data.narratives.get("growth_strategy", "")

        y = lay.content_top

        if narrative:
            add_summary_textbox(slide, narrative, top=y, tokens=tokens)
            y += 0.7

        if gs:
            if gs.organic_growth:
                add_sub_header_bar(
                    slide, "유기적 성장", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide, gs.organic_growth, top=y, height=1.0, tokens=tokens
                )
                y += 1.2

            if gs.new_business:
                add_sub_header_bar(
                    slide, "신규 사업", top=y, tokens=tokens
                )
                y += 0.45
                add_bullet_list(
                    slide, gs.new_business, top=y, height=1.0, tokens=tokens
                )
                y += 1.2

            if gs.ma_targets:
                add_sub_header_bar(slide, "M&A 전략", top=y, tokens=tokens)
                y += 0.45
                add_bullet_list(
                    slide, gs.ma_targets, top=y, height=1.0, tokens=tokens
                )
                y += 1.2

            # 로드맵
            if gs.roadmap:
                add_sub_header_bar(slide, "로드맵", top=y, tokens=tokens)
                y += 0.45
                roadmap_lines = []
                for year, goals in sorted(gs.roadmap.items()):
                    roadmap_lines.append(f"{year}: {', '.join(goals)}")
                add_body_textbox(
                    slide,
                    "\n".join(roadmap_lines),
                    top=y,
                    height=1.5,
                    tokens=tokens,
                )

        return [slide]
