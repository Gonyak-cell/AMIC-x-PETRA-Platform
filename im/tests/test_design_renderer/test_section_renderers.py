"""섹션 렌더러 테스트 — 레지스트리 18종/HTML/PPTX 출력."""

import pytest

from src.design_renderer.design_tokens import DEFAULT_TOKENS
from src.design_renderer.im_document import IMDocumentData, SECTION_IDS
from src.design_renderer.pptx_engine.slide_factory import SlideFactory
from src.design_renderer.pptx_engine.template_manager import TemplateManager
from src.design_renderer.section_renderers import (
    RENDERER_REGISTRY,
    get_renderer,
)


@pytest.fixture
def manager() -> TemplateManager:
    return TemplateManager(tokens=DEFAULT_TOKENS)


class TestRendererRegistry:
    """렌더러 레지스트리."""

    def test_all_21_registered(self):
        """21개 렌더러 모두 등록됨 (19 기본 + 2 산업)."""
        assert len(RENDERER_REGISTRY) == 21

    def test_all_section_ids_registered(self):
        """SECTION_IDS의 모든 ID가 등록됨."""
        for section_id in SECTION_IDS:
            assert section_id in RENDERER_REGISTRY, (
                f"'{section_id}' 미등록"
            )

    def test_get_renderer_returns_instance(self):
        """get_renderer() → 올바른 인스턴스."""
        renderer = get_renderer("cover")
        assert renderer is not None
        assert renderer.section_id == "cover"

    def test_get_renderer_unknown_raises(self):
        """미등록 ID → KeyError."""
        with pytest.raises(KeyError, match="미등록"):
            get_renderer("nonexistent_section")


class TestRenderersHtmlOutput:
    """모든 렌더러의 HTML 출력 검증."""

    def test_all_renderers_produce_html(self, full_data: IMDocumentData):
        """18개 렌더러 모두 비어있지 않은 HTML 리스트 반환.

        toc_divider는 current_section 없이 호출 시 빈 리스트를 반환할 수 있음.
        """
        for section_id in full_data.get_active_sections():
            renderer = get_renderer(section_id)
            # toc_divider는 current_section 인자가 필요
            if section_id == "toc_divider":
                html_slides = renderer.render_html(
                    full_data, tokens=DEFAULT_TOKENS, current_section="executive_summary"
                )
            else:
                html_slides = renderer.render_html(full_data, tokens=DEFAULT_TOKENS)
            assert isinstance(html_slides, list), (
                f"'{section_id}' render_html()이 list가 아님"
            )
            assert len(html_slides) >= 1, (
                f"'{section_id}' render_html()이 빈 리스트"
            )
            for slide_html in html_slides:
                assert isinstance(slide_html, str)
                assert len(slide_html) > 0


class TestRenderersPptxOutput:
    """모든 렌더러의 PPTX 출력 검증."""

    def test_all_renderers_produce_pptx(
        self, full_data: IMDocumentData, manager: TemplateManager
    ):
        """18개 렌더러 모두 비어있지 않은 Slide 리스트 반환.

        toc_divider는 current_section 없이 호출 시 빈 리스트를 반환할 수 있음.
        """
        for section_id in full_data.get_active_sections():
            prs = manager.new_presentation()
            factory = SlideFactory(manager, prs=prs, tokens=DEFAULT_TOKENS)

            renderer = get_renderer(section_id)
            # toc_divider는 current_section 인자가 필요
            if section_id == "toc_divider":
                pptx_slides = renderer.render_pptx(
                    factory, full_data, prs=prs, tokens=DEFAULT_TOKENS,
                    current_section="executive_summary"
                )
            else:
                pptx_slides = renderer.render_pptx(
                    factory, full_data, prs=prs, tokens=DEFAULT_TOKENS
                )
            assert isinstance(pptx_slides, list), (
                f"'{section_id}' render_pptx()가 list가 아님"
            )
            assert len(pptx_slides) >= 1, (
                f"'{section_id}' render_pptx()가 빈 리스트"
            )
