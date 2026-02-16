"""PDF 출력 테스트 — HTML 빌드 + PDF 변환."""

import pytest

from src.design_renderer.design_tokens import DEFAULT_TOKENS
from src.design_renderer.pdf_engine import build_watermark_css, generate_pdf
from src.design_renderer.pdf_output.html_builder import (
    build_html_document,
    build_slide_html,
)


class TestBuildSlideHtml:
    """단일 슬라이드 HTML 래퍼 (Tier 1 — 순수 문자열)."""

    def test_basic_structure(self):
        """기본 슬라이드 구조."""
        html = build_slide_html(
            "<p>내용</p>",
            title="테스트 슬라이드",
            slide_class="slide-test",
        )
        assert 'class="slide slide-test"' in html
        assert "테스트 슬라이드" in html
        assert "내용" in html

    def test_with_footnote(self):
        """각주 포함."""
        html = build_slide_html(
            "<p>내용</p>",
            footnote_html="<span>출처: DART</span>",
        )
        assert "DART" in html
        assert "slide-footnote" in html

    def test_empty_content(self):
        """빈 콘텐츠."""
        html = build_slide_html("")
        assert 'class="slide"' in html


class TestBuildHtmlDocument:
    """전체 HTML 문서 조립."""

    def test_complete_document(self):
        """CSS + 폰트 + 섹션 포함 문서."""
        sections = [
            '<div class="slide">슬라이드 1</div>',
            '<div class="slide">슬라이드 2</div>',
        ]
        html = build_html_document(sections, title="Test IM")
        assert "<!DOCTYPE html>" in html
        assert "<title>Test IM</title>" in html
        assert "슬라이드 1" in html
        assert "슬라이드 2" in html
        assert "<style>" in html

    def test_page_numbers(self):
        """페이지 번호 삽입."""
        sections = [
            '<div class="slide"><div class="slide-page-number"></div></div>',
            '<div class="slide"><div class="slide-page-number"></div></div>',
        ]
        html = build_html_document(sections, page_numbers=True)
        # 첫 페이지(표지)는 번호 없음
        assert "2 / 2" in html


class TestBuildWatermarkCss:
    """워터마크 CSS 생성."""

    def test_center_diagonal(self):
        """중앙 대각선 워터마크 CSS."""
        css = build_watermark_css(
            "CONFIDENTIAL",
            position="center_diagonal",
        )
        assert "CONFIDENTIAL" in css
        assert "rotate(-45deg)" in css
        assert ".slide::after" in css

    def test_top_center(self):
        """상단 중앙 워터마크."""
        css = build_watermark_css("SECRET", position="top_center")
        assert "SECRET" in css
        assert "top: 5%" in css


class TestGeneratePdf:
    """PDF 생성 (Playwright/WeasyPrint 필요)."""

    @pytest.mark.requires_browser
    def test_generates_pdf_bytes(self):
        """HTML → PDF 바이트 생성."""
        html = """<!DOCTYPE html>
        <html><head><style>@page{size:10in 7in;margin:0}</style></head>
        <body><div>테스트</div></body></html>"""
        pdf_bytes = generate_pdf(html, tokens=DEFAULT_TOKENS)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b"%PDF"  # PDF magic bytes

    @pytest.mark.requires_browser
    def test_saves_to_file(self, tmp_output):
        """PDF 파일 저장."""
        html = """<!DOCTYPE html>
        <html><head></head><body><p>Test</p></body></html>"""
        out = tmp_output / "test.pdf"
        generate_pdf(html, output_path=str(out), tokens=DEFAULT_TOKENS)
        assert out.exists()
        assert out.stat().st_size > 0
