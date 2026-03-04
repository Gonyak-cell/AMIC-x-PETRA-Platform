"""DM Valuation Analysis 별칭 렌더러.

기존 ValuationRenderer에 타이틀만 변경하여 재사용.
tm_aliases.py 패턴과 동일.
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
class DmValuationRenderer(BaseSectionRenderer):
    """DM Valuation Analysis 슬라이드 렌더러 (valuation 기반 별칭)."""

    section_id = "dm_valuation"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors

        narrative = html_escape(
            data.narratives.get("dm_valuation", "")
            or data.narratives.get("valuation", "")
        )
        ds = data.deal_structure

        # 밸류에이션 요약
        val_html = ""
        if ds:
            items: list[tuple[str, str]] = []
            if ds.valuation_method:
                items.append(("방법론", ds.valuation_method))
            if ds.valuation_low is not None and ds.valuation_high is not None:
                items.append(
                    ("범위", f"{ds.valuation_low:,.0f} ~ {ds.valuation_high:,.0f}억원")
                )
            elif ds.valuation_low is not None:
                items.append(("밸류에이션", f"{ds.valuation_low:,.0f}억원"))

            if items:
                cards = ""
                for label, value in items:
                    cards += (
                        f'<div style="text-align:center;padding:0.6em;'
                        f'background:{c.bg_light_green};border-radius:4px;">'
                        f'<div style="font-size:9pt;color:{c.text_secondary};">'
                        f"{html_escape(label)}</div>"
                        f'<div style="font-size:14pt;font-weight:bold;'
                        f'color:{c.primary};">{html_escape(value)}</div></div>'
                    )
                val_html = (
                    f'<div style="display:grid;grid-template-columns:'
                    f"repeat({min(len(items), 3)}, 1fr);gap:0.8em;"
                    f'margin-bottom:1em;">{cards}</div>'
                )

        narrative_html = ""
        if narrative:
            narrative_html = (
                f'<p style="font-size:10pt;color:{c.text_body};'
                f'line-height:1.6;">{narrative}</p>'
            )

        content = f"{val_html}{narrative_html}"
        return [
            build_slide_html(
                content,
                title="Valuation Analysis",
                slide_class="slide-dm-valuation",
                tokens=tokens,
            )
        ]

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        import copy

        from src.design_renderer.section_renderers.valuation import ValuationRenderer

        # 내러티브 키 매핑 — 원본 data 변경 방지를 위해 shallow copy 사용
        delegate_data = copy.copy(data)
        if "dm_valuation" in data.narratives and "valuation" not in data.narratives:
            delegate_data.narratives = {
                **data.narratives,
                "valuation": data.narratives["dm_valuation"],
            }

        delegate = ValuationRenderer()
        return delegate.render_pptx(factory, delegate_data, prs=prs, tokens=tokens)
