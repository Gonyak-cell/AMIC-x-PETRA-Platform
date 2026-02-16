"""웹사이트 브랜드 자산 통합 추출기 (T-B08).

> 마지막 수정: 2026-02-10 22:00:00

Playwright 기반으로 웹사이트를 크롤링하여
로고 탐지 + 색상 추출을 하나의 파이프라인으로 오케스트레이션한다.
"""

from __future__ import annotations

import logging
from io import BytesIO

import httpx
from PIL import Image
from playwright.async_api import async_playwright

from src.brand_extractor.color.classifier import ColorClassifier
from src.brand_extractor.color.extractor import ColorExtractor
from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.exceptions import WebsiteAccessError
from src.brand_extractor.logo.detector import LogoDetector
from src.brand_extractor.logo.processor import LogoProcessor
from src.brand_extractor.logo.scorer import LogoScorer
from src.brand_extractor.models import BrandAssets

logger = logging.getLogger(__name__)


class WebsiteExtractor:
    """Playwright 기반 웹사이트에서 브랜드 자산을 통합 추출한다.

    파이프라인:
    1. Playwright로 페이지 렌더링 + HTML 취득
    2. LogoDetector → 로고 후보 탐지
    3. LogoScorer → 최고 점수 로고 선택
    4. LogoProcessor → 로고 다운로드/저장
    5. 로고 이미지에서 ColorExtractor → 색상 추출
    6. ColorClassifier → primary/secondary 분류
    7. BrandAssets 조립

    Examples:
        >>> extractor = WebsiteExtractor(config)
        >>> brand = await extractor.extract("https://example.com", "Example Inc")
        >>> brand.source
        'website'
    """

    def __init__(self, config: BrandExtractorConfig) -> None:
        """초기화.

        Args:
            config: Brand Extractor 설정.
        """
        self._config = config
        self._logo_detector = LogoDetector()
        self._logo_scorer = LogoScorer(config)
        self._logo_processor = LogoProcessor(config)
        self._color_extractor = ColorExtractor(n_colors=config.max_colors)
        self._color_classifier = ColorClassifier()

    async def extract(self, url: str, company_name: str = "") -> BrandAssets:
        """웹사이트에서 브랜드 자산을 추출한다.

        Args:
            url: 웹사이트 URL (예: "https://samsung.com").
            company_name: 기업명.

        Returns:
            웹사이트에서 추출한 BrandAssets.
            confidence=0.6~0.8, source="website".

        Raises:
            WebsiteAccessError: 웹사이트 접근/렌더링 실패 시.
        """
        warnings: list[str] = []
        logo_dark_path = ""
        logo_url = ""
        primary_color = ""
        secondary_color = ""
        additional_colors: list[str] = []
        confidence = 0.6

        # 1. Playwright로 페이지 렌더링
        html = await self._fetch_page_html(url)

        # 2. 로고 탐지
        candidates = self._logo_detector.detect_from_html(html, url)

        if candidates:
            # 3. 스코어링
            scored = await self._logo_scorer.score_candidates(candidates)
            best = scored[0]
            logo_url = best.url

            # 4. 로고 다운로드/저장
            try:
                logo_dark_path = await self._logo_processor.download_and_save(
                    best.url,
                    prefix=self._sanitize_prefix(company_name),
                    variant="dark",
                )
            except Exception as e:
                warnings.append(f"로고 저장 실패: {e}")
                logger.warning("로고 저장 실패: %s", e)

            # 5. 로고 이미지에서 색상 추출
            try:
                logo_colors = await self._extract_colors_from_logo(best.url)
                classified = self._color_classifier.classify(logo_colors)

                for c in classified:
                    if c.role == "primary" and not primary_color:
                        primary_color = c.hex
                    elif c.role == "secondary" and not secondary_color:
                        secondary_color = c.hex
                    elif c.role not in ("primary", "secondary") and c.hex:
                        additional_colors.append(c.hex)

                if primary_color:
                    confidence = 0.8
            except Exception as e:
                warnings.append(f"로고 색상 추출 실패: {e}")
                logger.warning("로고 색상 추출 실패: %s", e)
        else:
            warnings.append("로고 후보를 찾을 수 없습니다")

        # 6. 색상 미추출 시 스크린샷 폴백 (생략 — 폴백 체인으로 위임)

        return BrandAssets(
            company_name=company_name,
            primary_color=primary_color or "#0F3A32",
            secondary_color=secondary_color or "#26C260",
            logo_dark_path=logo_dark_path,
            logo_url=logo_url,
            confidence=confidence if primary_color else 0.4,
            source="website",
            additional_colors=additional_colors,
            warnings=warnings,
        )

    async def _fetch_page_html(self, url: str) -> str:
        """Playwright로 페이지를 렌더링하여 HTML을 반환한다.

        Args:
            url: 대상 URL.

        Returns:
            렌더링된 HTML 문자열.

        Raises:
            WebsiteAccessError: 페이지 접근 실패 시.
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(
                        url,
                        timeout=self._config.timeout * 1000,
                        wait_until="domcontentloaded",
                    )
                    html = await page.content()
                finally:
                    await browser.close()
        except Exception as e:
            raise WebsiteAccessError(url=url, original_error=str(e)) from e

        return html

    async def _extract_colors_from_logo(self, logo_url: str) -> list:
        """로고 URL에서 이미지를 다운로드하여 색상을 추출한다.

        Args:
            logo_url: 로고 이미지 URL.

        Returns:
            ExtractedColor 리스트.
        """
        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            resp = await client.get(logo_url)
            resp.raise_for_status()

        img = Image.open(BytesIO(resp.content))
        return self._color_extractor.extract_from_image(img)

    @staticmethod
    def _sanitize_prefix(name: str) -> str:
        """파일명 접두사용으로 문자열을 정규화한다.

        Args:
            name: 기업명 등.

        Returns:
            영숫자와 밑줄만 포함한 문자열. 빈 값이면 "brand".
        """
        sanitized = "".join(c if c.isalnum() else "_" for c in name).strip("_")
        return sanitized[:50] if sanitized else "brand"
