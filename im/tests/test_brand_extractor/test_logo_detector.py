"""LogoDetector 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from src.brand_extractor.logo.detector import LogoDetector


class TestLogoDetector:
    """LogoDetector 로고 탐지 테스트."""

    def setup_method(self) -> None:
        """테스트 초기화."""
        self.detector = LogoDetector()

    def test_detect_og_image(self, sample_html_with_logo: str) -> None:
        """og:image 메타 태그에서 로고 탐지."""
        candidates = self.detector.detect_from_html(
            sample_html_with_logo, "https://example.com"
        )
        og_candidates = [c for c in candidates if c.source == "og:image"]
        assert len(og_candidates) >= 1
        assert og_candidates[0].url == "https://example.com/og-logo.png"

    def test_detect_apple_touch_icon(self, sample_html_with_logo: str) -> None:
        """apple-touch-icon에서 로고 탐지."""
        candidates = self.detector.detect_from_html(
            sample_html_with_logo, "https://example.com"
        )
        touch_candidates = [c for c in candidates if c.source == "apple-touch-icon"]
        assert len(touch_candidates) >= 1

    def test_detect_favicon(self, sample_html_with_logo: str) -> None:
        """favicon에서 로고 탐지."""
        candidates = self.detector.detect_from_html(
            sample_html_with_logo, "https://example.com"
        )
        favicon_candidates = [c for c in candidates if c.source == "favicon"]
        assert len(favicon_candidates) >= 1

    def test_detect_css_selector(self, sample_html_with_logo: str) -> None:
        """CSS 셀렉터 기반 로고 탐지."""
        candidates = self.detector.detect_from_html(
            sample_html_with_logo, "https://example.com"
        )
        css_candidates = [c for c in candidates if c.source == "css-selector"]
        # img[alt*="logo"]에 의해 탐지되어야 함
        assert len(css_candidates) >= 1

    def test_empty_html_returns_empty(self, sample_html_no_logo: str) -> None:
        """로고 없는 HTML에서 빈 리스트 반환."""
        candidates = self.detector.detect_from_html(
            sample_html_no_logo, "https://example.com"
        )
        assert candidates == []

    def test_url_normalization(self) -> None:
        """상대 URL이 절대 URL로 변환되는지 확인."""
        html = '<html><head><link rel="icon" href="/favicon.png"></head></html>'
        candidates = self.detector.detect_from_html(html, "https://example.com")
        assert candidates[0].url == "https://example.com/favicon.png"

    def test_no_duplicate_urls(self) -> None:
        """동일 URL 중복 제거 확인."""
        html = """
        <html><head>
            <link rel="icon" href="/logo.png">
            <link rel="shortcut icon" href="/logo.png">
        </head></html>
        """
        candidates = self.detector.detect_from_html(html, "https://example.com")
        urls = [c.url for c in candidates]
        assert len(urls) == len(set(urls))

    def test_format_guessing(self) -> None:
        """URL 확장자에서 포맷 추정."""
        assert LogoDetector._guess_format("https://example.com/logo.svg") == "svg"
        assert LogoDetector._guess_format("https://example.com/logo.png") == "png"
        assert LogoDetector._guess_format("https://example.com/logo.jpg") == "jpeg"
        assert LogoDetector._guess_format("https://example.com/logo.ico") == "ico"
        assert LogoDetector._guess_format("https://example.com/logo") == ""
