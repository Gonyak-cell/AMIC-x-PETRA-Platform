"""BrandfetchClient 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.exceptions import BrandfetchAPIError
from src.brand_extractor.extractors.brandfetch import BrandfetchClient


class TestBrandfetchClient:
    """BrandfetchClient API 클라이언트 테스트."""

    @pytest.fixture
    def config(self) -> BrandExtractorConfig:
        """테스트용 설정."""
        return BrandExtractorConfig(
            brandfetch_api_key="test-key-12345",
            brandfetch_base_url="https://api.brandfetch.io/v2",
            timeout=10,
        )

    @pytest.mark.asyncio
    async def test_extract_success(
        self,
        config: BrandExtractorConfig,
        brandfetch_success_response: dict,
    ) -> None:
        """정상 응답 파싱 테스트."""
        mock_response = httpx.Response(
            200,
            json=brandfetch_success_response,
            request=httpx.Request("GET", "https://api.brandfetch.io/v2/brands/samsung.com"),
        )

        async with BrandfetchClient(config) as client:
            with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                brand = await client.extract("samsung.com")

        assert brand.source == "brandfetch"
        assert brand.confidence == 0.95
        assert brand.company_name == "Samsung Electronics"
        assert brand.primary_color == "#1428A0"
        assert brand.secondary_color == "#00A1E0"
        assert brand.logo_url == "https://cdn.brandfetch.io/samsung/logo.svg"

    @pytest.mark.asyncio
    async def test_extract_401_error(self, config: BrandExtractorConfig) -> None:
        """401 인증 실패 테스트."""
        mock_response = httpx.Response(
            401,
            json={"error": "Unauthorized"},
            request=httpx.Request("GET", "https://api.brandfetch.io/v2/brands/test.com"),
        )

        async with BrandfetchClient(config) as client:
            with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                with pytest.raises(BrandfetchAPIError) as exc_info:
                    await client.extract("test.com")
                assert exc_info.value.details["status_code"] == 401

    @pytest.mark.asyncio
    async def test_extract_404_error(self, config: BrandExtractorConfig) -> None:
        """404 도메인 미등록 테스트."""
        mock_response = httpx.Response(
            404,
            json={"error": "Not Found"},
            request=httpx.Request("GET", "https://api.brandfetch.io/v2/brands/unknown.com"),
        )

        async with BrandfetchClient(config) as client:
            with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                with pytest.raises(BrandfetchAPIError) as exc_info:
                    await client.extract("unknown.com")
                assert exc_info.value.details["status_code"] == 404

    @pytest.mark.asyncio
    async def test_extract_429_rate_limit(self, config: BrandExtractorConfig) -> None:
        """429 Rate Limit 테스트."""
        mock_response = httpx.Response(
            429,
            json={"error": "Too Many Requests"},
            request=httpx.Request("GET", "https://api.brandfetch.io/v2/brands/test.com"),
        )

        async with BrandfetchClient(config) as client:
            with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                with pytest.raises(BrandfetchAPIError) as exc_info:
                    await client.extract("test.com")
                assert exc_info.value.details["status_code"] == 429

    @pytest.mark.asyncio
    async def test_extract_without_context_manager(
        self, config: BrandExtractorConfig
    ) -> None:
        """async with 없이 호출하면 에러."""
        client = BrandfetchClient(config)
        with pytest.raises(BrandfetchAPIError, match="초기화되지 않았습니다"):
            await client.extract("test.com")

    @pytest.mark.asyncio
    async def test_extract_missing_colors(self, config: BrandExtractorConfig) -> None:
        """색상 없는 응답에서 AMIC 기본값 폴백."""
        response_data = {
            "name": "NoColor Corp",
            "domain": "nocolor.com",
            "logos": [],
            "colors": [],
        }
        mock_response = httpx.Response(
            200,
            json=response_data,
            request=httpx.Request("GET", "https://api.brandfetch.io/v2/brands/nocolor.com"),
        )

        async with BrandfetchClient(config) as client:
            with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                brand = await client.extract("nocolor.com")

        # 색상이 없으면 AMIC 기본값 사용
        assert brand.primary_color == "#0F3A32"
        assert brand.secondary_color == "#26C260"
        assert len(brand.warnings) >= 1
