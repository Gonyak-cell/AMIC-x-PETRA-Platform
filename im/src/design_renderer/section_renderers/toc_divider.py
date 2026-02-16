"""TOC 구분(Table of Contents Divider) 섹션 렌더러.

각 주요 섹션 전에 삽입되는 TOC 구분 슬라이드.
현재 활성 섹션이 ALL CAPS + AMIC 컬러로 하이라이트된다.
"""

from __future__ import annotations

import logging
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData
from src.design_renderer.pptx_engine.toc_builder import (
    build_toc_slide,
    build_toc_slide_html,
)
from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer

logger = logging.getLogger(__name__)


@register_renderer
class TOCDividerRenderer(BaseSectionRenderer):
    """TOC 구분 슬라이드 렌더러.

    render_html/render_pptx에 current_section 키워드 인자를 추가로 받는다.
    """

    section_id = "toc_divider"

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
        current_section: str = "",
    ) -> list[str]:
        tokens = tokens or DEFAULT_TOKENS

        sections = data.get_active_sections()
        if not current_section:
            return []

        html = build_toc_slide_html(
            sections,
            current_section,
            tokens=tokens,
        )
        return [html]

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
        current_section: str = "",
    ) -> list[Any]:
        tokens = tokens or DEFAULT_TOKENS

        sections = data.get_active_sections()
        if not current_section:
            return []

        slide = factory._manager.add_slide("blank", prs)
        build_toc_slide(
            slide,
            sections,
            current_section,
            tokens=tokens,
        )
        return [slide]
