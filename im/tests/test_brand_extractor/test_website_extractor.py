"""WebsiteExtractor 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.exceptions import WebsiteAccessError
from src.brand_extractor.extractors.website import WebsiteExtractor


class TestWebsiteExtractor:
    """WebsiteExtractor 웹사이트 통합 추출 테스트."""

    @pytest.fixture
    def config(self) -> BrandExtractorConfig:
        """테스트용 설정."""
        return BrandExtractorConfig(timeout=5, max_colors=3)

    @pytest.mark.asyncio
    async def test_extract_with_mocked_playwright(
        self,
        config: BrandExtractorConfig,
        sample_html_with_logo: str,
    ) -> None:
        """Playwright 모킹 기반 추출 테스트."""
        extractor = WebsiteExtractor(config)

        # Playwright 모킹
        with patch.object(
            extractor, "_fetch_page_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_html_with_logo

            # 로고 스코어링/다운로드/색상 추출 모킹
            with patch.object(
                extractor._logo_scorer, "score_candidates", new_callable=AsyncMock
            ) as mock_score:
                mock_candidate = MagicMock()
                mock_candidate.url = "https://example.com/logo.png"
                mock_candidate.score = 0.8
                mock_score.return_value = [mock_candidate]

                with patch.object(
                    extractor._logo_processor,
                    "download_and_save",
                    new_callable=AsyncMock,
                ) as mock_save:
                    mock_save.return_value = "/tmp/brand_dark.png"

                    with patch.object(
                        extractor,
                        "_extract_colors_from_logo",
                        new_callable=AsyncMock,
                    ) as mock_colors:
                        mock_colors.return_value = []

                        brand = await extractor.extract(
                            "https://example.com", "테스트 기업"
                        )

        assert brand.source == "website"
        assert brand.company_name == "테스트 기업"
        assert brand.logo_dark_path == "/tmp/brand_dark.png"

    @pytest.mark.asyncio
    async def test_extract_timeout(self, config: BrandExtractorConfig) -> None:
        """웹사이트 접근 타임아웃 시 WebsiteAccessError."""
        extractor = WebsiteExtractor(config)

        with patch.object(
            extractor, "_fetch_page_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = WebsiteAccessError(
                url="https://slow.example.com",
                original_error="Timeout",
            )
            with pytest.raises(WebsiteAccessError):
                await extractor.extract("https://slow.example.com")

    @pytest.mark.asyncio
    async def test_extract_no_logo_found(
        self,
        config: BrandExtractorConfig,
        sample_html_no_logo: str,
    ) -> None:
        """로고 없는 페이지에서도 BrandAssets 반환 (폴백 색상)."""
        extractor = WebsiteExtractor(config)

        with patch.object(
            extractor, "_fetch_page_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_html_no_logo
            brand = await extractor.extract("https://nologos.example.com", "NoLogo")

        assert brand.source == "website"
        assert brand.logo_url == ""
        assert "로고 후보를 찾을 수 없습니다" in brand.warnings

    def test_sanitize_prefix(self) -> None:
        """파일명 접두사 정규화."""
        assert WebsiteExtractor._sanitize_prefix("삼성전자") == "삼성전자"
        assert WebsiteExtractor._sanitize_prefix("A B C") == "A_B_C"
        assert WebsiteExtractor._sanitize_prefix("") == "brand"
        assert WebsiteExtractor._sanitize_prefix("a/b\\c") == "a_b_c"
