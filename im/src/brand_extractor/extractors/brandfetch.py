"""Brandfetch API 클라이언트 (T-B02).

> 마지막 수정: 2026-02-10 22:00:00

Brandfetch API v2를 사용하여 도메인에서 브랜드 자산(로고, 색상)을
자동으로 수집하는 비동기 클라이언트.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.exceptions import BrandfetchAPIError
from src.brand_extractor.models import BrandAssets

logger = logging.getLogger(__name__)


class BrandfetchClient:
    """Brandfetch API v2 비동기 클라이언트.

    Brandfetch API를 통해 기업 도메인에서 로고, 색상, 폰트 등
    브랜드 자산을 자동으로 수집한다.

    Examples:
        >>> async with BrandfetchClient(config) as client:
        ...     brand = await client.extract("samsung.com")
        ...     brand.source
        'brandfetch'
    """

    def __init__(self, config: BrandExtractorConfig) -> None:
        """초기화.

        Args:
            config: Brand Extractor 설정 (API 키, URL 등).
        """
        self._api_key = config.brandfetch_api_key
        self._base_url = config.brandfetch_base_url.rstrip("/")
        self._timeout = config.timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> BrandfetchClient:
        """비동기 컨텍스트 매니저 진입."""
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        """비동기 컨텍스트 매니저 종료."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def extract(self, domain: str) -> BrandAssets:
        """도메인에서 브랜드 자산을 추출한다.

        Args:
            domain: 기업 도메인 (예: "samsung.com").

        Returns:
            Brandfetch API 응답을 파싱한 BrandAssets.
            confidence=0.95, source="brandfetch".

        Raises:
            BrandfetchAPIError: API 호출 실패 시.
        """
        if not self._client:
            raise BrandfetchAPIError(
                status_code=0,
                original_error="클라이언트가 초기화되지 않았습니다. async with를 사용하세요.",
            )

        url = f"{self._base_url}/brands/{domain}"
        logger.info("Brandfetch API 호출: %s", url)

        try:
            resp = await self._client.get(url)
        except httpx.TimeoutException as e:
            raise BrandfetchAPIError(
                status_code=0,
                original_error=f"타임아웃: {e}",
            ) from e
        except httpx.HTTPError as e:
            raise BrandfetchAPIError(
                status_code=0,
                original_error=f"네트워크 오류: {e}",
            ) from e

        if resp.status_code != 200:
            raise BrandfetchAPIError(
                status_code=resp.status_code,
                original_error=self._error_message(resp.status_code),
            )

        data = resp.json()
        return self._parse_response(data, domain)

    def _parse_response(self, data: dict[str, Any], domain: str) -> BrandAssets:
        """Brandfetch API 응답을 BrandAssets로 파싱한다.

        Args:
            data: API 응답 JSON.
            domain: 요청 도메인.

        Returns:
            파싱된 BrandAssets.
        """
        warnings: list[str] = []

        # 회사명
        company_name = data.get("name", domain)

        # 로고 추출
        logo_url = ""
        logos = data.get("logos", [])
        for logo in logos:
            formats = logo.get("formats", [])
            # 가장 큰 포맷 선택
            best_format = self._select_best_logo_format(formats)
            if best_format:
                logo_url = best_format.get("src", "")
                break
        if not logo_url:
            warnings.append("Brandfetch: 로고를 찾을 수 없습니다")

        # 색상 추출
        primary_color = ""
        secondary_color = ""
        colors = data.get("colors", [])
        for color_entry in colors:
            hex_val = color_entry.get("hex", "")
            color_type = color_entry.get("type", "")
            if not hex_val:
                continue
            # "#" 접두사 보장
            if not hex_val.startswith("#"):
                hex_val = f"#{hex_val}"
            if color_type in ("dark", "primary") and not primary_color:
                primary_color = hex_val
            elif color_type in ("accent", "light", "secondary") and not secondary_color:
                secondary_color = hex_val

        if not primary_color:
            warnings.append("Brandfetch: primary 색상을 찾을 수 없습니다")
        if not secondary_color:
            warnings.append("Brandfetch: secondary 색상을 찾을 수 없습니다")

        # 추가 색상
        additional = [
            c.get("hex", "") for c in colors if c.get("hex") and c.get("hex") != primary_color
        ]

        return BrandAssets(
            company_name=company_name,
            primary_color=primary_color or "#0F3A32",
            secondary_color=secondary_color or "#26C260",
            logo_url=logo_url,
            confidence=0.95,
            source="brandfetch",
            additional_colors=[c if c.startswith("#") else f"#{c}" for c in additional if c],
            warnings=warnings,
        )

    @staticmethod
    def _select_best_logo_format(formats: list[dict[str, Any]]) -> dict[str, Any] | None:
        """로고 포맷 중 최적을 선택한다 (SVG > PNG > 나머지).

        Args:
            formats: Brandfetch 로고 포맷 리스트.

        Returns:
            최적 포맷 딕셔너리, 없으면 None.
        """
        priority = {"image/svg+xml": 0, "image/png": 1, "image/jpeg": 2}
        sorted_formats = sorted(
            formats,
            key=lambda f: priority.get(f.get("format", ""), 99),
        )
        return sorted_formats[0] if sorted_formats else None

    @staticmethod
    def _error_message(status_code: int) -> str:
        """HTTP 상태 코드별 오류 메시지를 반환한다.

        Args:
            status_code: HTTP 상태 코드.

        Returns:
            사람이 읽을 수 있는 오류 메시지.
        """
        messages = {
            401: "인증 실패 — API 키를 확인하세요",
            403: "접근 거부 — API 키 권한을 확인하세요",
            404: "도메인 미등록 — Brandfetch에 해당 도메인이 없습니다",
            429: "요청 한도 초과 — Rate Limit에 도달했습니다",
        }
        return messages.get(status_code, f"HTTP {status_code}")
