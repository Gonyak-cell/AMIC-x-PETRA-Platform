"""산업별 KPI 대시보드 섹션 렌더러 (A2).

> 마지막 수정: 2026-02-11 14:00:00

IndustryModule의 KPI 정의를 동적으로 읽어 카드 그리드를 렌더링하고,
industry_kpi 섹션 대상 차트 이미지를 삽입한다.
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


def _format_kpi_value(
    kpi_id: str,
    industry_data: dict[str, Any],
    display_format: str,
) -> str:
    """industry_data에서 KPI 값을 추출하여 포맷팅한다."""
    raw = industry_data.get(kpi_id)
    if raw is None:
        return "N/A"
    try:
        return display_format.format(raw)
    except (ValueError, TypeError):
        return str(raw)


@register_renderer
class IndustryKPIRenderer(BaseSectionRenderer):
    """산업별 KPI 대시보드 렌더러.

    IndustryModule.get_kpis()에서 KPI 정의를 가져오고,
    data.industry_data에서 실제 값을 매핑하여 카드 그리드를 생성한다.
    """

    section_id = "industry_kpi"

    def _get_module(self, data: IMDocumentData) -> Any | None:
        """산업 모듈을 조회한다. 미설정 시 None."""
        if not data.industry:
            return None
        try:
            from src.industry.registry import get_industry_module_safe

            return get_industry_module_safe(data.industry)
        except Exception:
            logger.warning("산업 모듈 조회 실패: %s", data.industry, exc_info=True)
            return None

    def _build_kpi_cards(
        self,
        data: IMDocumentData,
        module: Any,
    ) -> list[dict[str, str]]:
        """KPI 카드 데이터를 [{label, value}] 리스트로 변환."""
        industry_data = data.industry_data or {}
        cards: list[dict[str, str]] = []
        for kpi in module.get_kpis():
            value = _format_kpi_value(
                kpi.kpi_id,
                industry_data,
                kpi.display_format,
            )
            cards.append({"label": kpi.name_kr, "value": value})
        return cards

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        """산업별 KPI 대시보드 HTML 슬라이드를 반환한다."""
        module = self._get_module(data)
        if module is None:
            return []

        tokens = tokens or DEFAULT_TOKENS
        c = tokens.colors
        kpis = self._build_kpi_cards(data, module)

        # KPI 카드 그리드
        cards_html = ""
        for kpi in kpis:
            cards_html += (
                f'<div style="text-align:center;padding:0.6em;'
                f'background:{c.bg_cool_grey};border-radius:4px;">'
                f'<div style="font-size:9pt;color:{c.text_secondary};">'
                f"{html_escape(kpi['label'])}</div>"
                f'<div style="font-size:18pt;font-weight:bold;'
                f"color:{c.primary};font-family:'IBM Plex Mono',monospace;\">"
                f"{html_escape(kpi['value'])}</div></div>"
            )
        kpi_grid = (
            f'<div style="display:grid;grid-template-columns:'
            f"repeat({min(len(kpis), 4)}, 1fr);gap:0.8em;"
            f'margin-bottom:1em;">{cards_html}</div>'
        )

        # 차트 이미지
        chart_html = ""
        chart_list = (data.charts or {}).get("industry_kpi", [])
        for chart in chart_list:
            img_data = getattr(chart, "data", {}) or {}
            img_path = img_data.get("image_path", "")
            if img_path:
                chart_html += (
                    f'<div style="text-align:center;margin-top:1em;">'
                    f'<img src="{html_escape(str(img_path))}" '
                    f'style="max-width:100%;"/></div>'
                )

        title = f"{module.industry_name_kr} 핵심 KPI"
        content = f"{kpi_grid}{chart_html}"
        slide = build_slide_html(
            content,
            title=title,
            slide_class="slide-industry-kpi",
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
        """산업별 KPI 대시보드 PPTX 슬라이드를 반환한다."""
        module = self._get_module(data)
        if module is None:
            return []

        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_chart_or_image,
            add_kpi_grid,
        )

        title = f"{module.industry_name_kr} 핵심 KPI"
        slide = factory.add_content_slide(title=title)
        kpis = self._build_kpi_cards(data, module)
        result = []

        y = lay.content_top

        if kpis:
            add_kpi_grid(
                slide,
                kpis,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
            )
            y += 1.6

        # 차트 삽입 (네이티브 또는 이미지)
        chart_list = (data.charts or {}).get("industry_kpi", [])
        for chart in chart_list:
            add_chart_or_image(slide, chart, top=y, tokens=tokens)
            y += 2.5

        result.append(slide)
        return result
