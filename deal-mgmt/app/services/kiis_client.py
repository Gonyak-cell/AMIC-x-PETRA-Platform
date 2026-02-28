"""KIIS 백엔드(:8001) API 호출 래퍼 — 모듈 간 연계."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

KIIS_BASE_URL = getattr(settings, "KIIS_API_URL", "http://kiis-api:8001/api/v1")

_MAX_RETRIES = 2
_RETRY_DELAY = 0.5  # seconds


class KIISClient:
    """KIIS(기업정보 조사 서비스) 클라이언트 — 커넥션 풀 재사용."""

    def __init__(self, base_url: str = KIIS_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        base_url=self.base_url,
                        timeout=self.timeout,
                    )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """HTTP 요청 + 재시도 (transient 오류 대응)."""
        client = await self._get_client()
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.request(method, path, **kwargs)
                resp.raise_for_status()
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    logger.warning("KIIS %s %s 재시도 %d/%d: %s", method, path, attempt + 1, _MAX_RETRIES, exc)
                    await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                    continue
            except httpx.HTTPStatusError:
                raise
        raise last_exc  # type: ignore[misc]

    async def search_company(self, name: str) -> list[dict]:
        """회사명으로 DART 기업 검색."""
        resp = await self._request_with_retry("GET", "/companies", params={"q": name})
        data = resp.json()
        return data.get("items", data) if isinstance(data, dict) else data

    async def get_company_detail(self, corp_code: str) -> dict:
        """기업 상세 정보 조회."""
        resp = await self._request_with_retry("GET", f"/companies/{corp_code}")
        return resp.json()

    async def get_financial_summary(self, corp_code: str) -> dict:
        """기업 요약재무 (매출/영업이익/순이익/부채비율) 조회."""
        resp = await self._request_with_retry("GET", f"/dart/companies/{corp_code}/financial-summary")
        return resp.json()

    async def search_gps(self, query: str) -> list[dict]:
        """GP(운용사) 검색."""
        resp = await self._request_with_retry("GET", "/kofia/gp", params={"search": query})
        data = resp.json()
        return data.get("items", data) if isinstance(data, dict) else data
