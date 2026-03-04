"""HTML 로고 탐지기 (T-B03).

> 마지막 수정: 2026-02-10 22:00:00

HTML 문서에서 로고 URL 후보를 탐지한다.
meta 태그, link 태그, CSS 셀렉터 기반의 다단계 탐지 전략을 사용한다.
"""

from __future__ import annotations

import logging
from typing import ClassVar
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.brand_extractor.models import LogoCandidate

logger = logging.getLogger(__name__)


class LogoDetector:
    """HTML에서 로고 URL 후보를 탐지한다.

    탐지 순서:
    1. <meta property="og:image"> — Open Graph 이미지
    2. <link rel="apple-touch-icon"> — Apple 터치 아이콘
    3. <link rel="icon"> — 파비콘 (PNG/SVG 우선)
    4. CSS 셀렉터 — header/nav 영역의 img 태그

    Examples:
        >>> detector = LogoDetector()
        >>> candidates = detector.detect_from_html(html, "https://example.com")
        >>> len(candidates) >= 1
        True
    """

    STRUCTURED_SOURCES: ClassVar[list[tuple[str, str, str]]] = [
        # (CSS 셀렉터, 속성명, 소스 라벨)
        ("meta[property='og:image']", "content", "og:image"),
        ("meta[name='og:image']", "content", "og:image"),
        ("link[rel='apple-touch-icon']", "href", "apple-touch-icon"),
        ("link[rel='apple-touch-icon-precomposed']", "href", "apple-touch-icon"),
        ("link[rel='icon'][type='image/png']", "href", "favicon"),
        ("link[rel='icon'][type='image/svg+xml']", "href", "favicon"),
        ("link[rel='icon'][sizes]", "href", "favicon"),
        ("link[rel='shortcut icon']", "href", "favicon"),
        ("link[rel='icon']", "href", "favicon"),
    ]

    CSS_SELECTORS: ClassVar[list[str]] = [
        'header img[class*="logo"]',
        'header img[alt*="logo"]',
        'nav img[class*="logo"]',
        ".logo img",
        "#logo img",
        'a[class*="logo"] img',
        'img[class*="logo"]',
        'img[alt*="logo"]',
    ]

    def detect_from_html(self, html: str, base_url: str) -> list[LogoCandidate]:
        """HTML 문자열에서 로고 후보를 추출한다.

        Args:
            html: 파싱할 HTML 문자열.
            base_url: 상대 URL 해석을 위한 기준 URL.

        Returns:
            LogoCandidate 리스트 (중복 제거, 탐지 순서 유지).
        """
        soup = BeautifulSoup(html, "html.parser")
        candidates: list[LogoCandidate] = []
        seen_urls: set[str] = set()

        # 1. 구조화된 소스 (meta, link 태그)
        for selector, attr, source_label in self.STRUCTURED_SOURCES:
            elements = soup.select(selector)
            for el in elements:
                raw_url = el.get(attr, "")
                if not raw_url:
                    continue
                url = urljoin(base_url, str(raw_url))
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                fmt = self._guess_format(url)
                candidates.append(
                    LogoCandidate(
                        url=url,
                        source=source_label,
                        format=fmt,
                    )
                )

        # 2. CSS 셀렉터 기반 탐지
        for selector in self.CSS_SELECTORS:
            elements = soup.select(selector)
            for el in elements:
                raw_url = el.get("src", "") or el.get("data-src", "")
                if not raw_url:
                    continue
                url = urljoin(base_url, str(raw_url))
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                fmt = self._guess_format(url)
                candidates.append(
                    LogoCandidate(
                        url=url,
                        source="css-selector",
                        format=fmt,
                    )
                )

        logger.info(
            "로고 후보 %d개 탐지: url='%s'",
            len(candidates),
            base_url,
        )
        return candidates

    @staticmethod
    def _guess_format(url: str) -> str:
        """URL 확장자로 이미지 포맷을 추정한다.

        Args:
            url: 이미지 URL.

        Returns:
            포맷 문자열 ("png" | "svg" | "jpeg" | "ico" | "").
        """
        lower = url.lower().split("?")[0]
        if lower.endswith(".svg"):
            return "svg"
        if lower.endswith(".png"):
            return "png"
        if lower.endswith((".jpg", ".jpeg")):
            return "jpeg"
        if lower.endswith(".ico"):
            return "ico"
        return ""
