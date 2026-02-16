"""Brand Extractor 통합 테스트 — extract_brand() E2E.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.brand_extractor import extract_brand
from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.exceptions import BrandfetchAPIError, WebsiteAccessError
from src.brand_extractor.models import BrandAssets
from src.design_renderer.design_tokens import IMDesignTokens


class TestExtractBrandIntegration:
    """extract_brand() 3단계 우선순위 체인 통합 테스트."""

    @pytest.fixture
    def config_no_api(self) -> BrandExtractorConfig:
        """API 키 없는 설정."""
        return BrandExtractorConfig(
            brandfetch_api_key="",
            timeout=5,
            fallback_enabled=True,
        )

    @pytest.fixture
    def config_with_api(self) -> BrandExtractorConfig:
        """API 키 있는 설정."""
        return BrandExtractorConfig(
            brandfetch_api_key="test-key",
            timeout=5,
            fallback_enabled=True,
        )

    @pytest.mark.asyncio
    async def test_fallback_when_no_api_and_website_fails(
        self,
        config_no_api: BrandExtractorConfig,
    ) -> None:
        """API 키 없고 웹사이트도 실패 → AMIC 폴백."""
        with patch(
            "src.brand_extractor.WebsiteExtractor.extract",
            new_callable=AsyncMock,
            side_effect=WebsiteAccessError(url="https://test.com", original_error="fail"),
        ):
            brand = await extract_brand(
                "test.com",
                company_name="테스트",
                config=config_no_api,
            )

        assert brand.source == "fallback"
        assert brand.primary_color == "#0F3A32"
        assert brand.company_name == "테스트"
        assert brand.confidence == 0.0

    @pytest.mark.asyncio
    async def test_brandfetch_success_skips_website(
        self,
        config_with_api: BrandExtractorConfig,
    ) -> None:
        """Brandfetch 성공 시 웹사이트 크롤링 건너뜀."""
        mock_brand = BrandAssets(
            company_name="BF Corp",
            primary_color="#1428A0",
            secondary_color="#00A1E0",
            confidence=0.95,
            source="brandfetch",
        )
        with patch(
            "src.brand_extractor.BrandfetchClient.extract",
            new_callable=AsyncMock,
            return_value=mock_brand,
        ), patch(
            "src.brand_extractor.BrandfetchClient.__aenter__",
            new_callable=AsyncMock,
        ) as mock_enter, patch(
            "src.brand_extractor.BrandfetchClient.__aexit__",
            new_callable=AsyncMock,
        ):
            mock_enter.return_value = AsyncMock(extract=AsyncMock(return_value=mock_brand))
            brand = await extract_brand(
                "bf.com",
                config=config_with_api,
            )

        assert brand.source == "brandfetch"
        assert brand.confidence == 0.95

    @pytest.mark.asyncio
    async def test_brandfetch_fails_falls_to_website(
        self,
        config_with_api: BrandExtractorConfig,
    ) -> None:
        """Brandfetch 실패 → 웹사이트 크롤링 시도."""
        mock_website_brand = BrandAssets(
            company_name="Website Corp",
            primary_color="#FF5733",
            confidence=0.7,
            source="website",
        )

        # __aexit__는 return_value=False로 설정하여 예외 suppress 방지
        mock_aexit = AsyncMock(return_value=False)

        with patch(
            "src.brand_extractor.BrandfetchClient.__aenter__",
            new_callable=AsyncMock,
        ) as mock_enter, patch(
            "src.brand_extractor.BrandfetchClient.__aexit__",
            mock_aexit,
        ):
            mock_client = AsyncMock()
            mock_client.extract = AsyncMock(
                side_effect=BrandfetchAPIError(status_code=404, original_error="Not found")
            )
            mock_enter.return_value = mock_client

            with patch(
                "src.brand_extractor.WebsiteExtractor.extract",
                new_callable=AsyncMock,
                return_value=mock_website_brand,
            ):
                brand = await extract_brand(
                    "website.com",
                    config=config_with_api,
                )

        assert brand.source == "website"
        assert brand.primary_color == "#FF5733"
        assert any("Brandfetch" in w for w in brand.warnings)

    @pytest.mark.asyncio
    async def test_brand_assets_to_design_tokens(
        self,
        config_no_api: BrandExtractorConfig,
    ) -> None:
        """BrandAssets → IMDesignTokens 변환 E2E."""
        with patch(
            "src.brand_extractor.WebsiteExtractor.extract",
            new_callable=AsyncMock,
            side_effect=WebsiteAccessError(url="https://test.com", original_error="fail"),
        ):
            brand = await extract_brand(
                "test.com",
                config=config_no_api,
            )

        tokens = IMDesignTokens.from_brand_assets(brand)
        assert tokens.colors.primary == brand.primary_color
        assert tokens.colors.accent == brand.secondary_color
