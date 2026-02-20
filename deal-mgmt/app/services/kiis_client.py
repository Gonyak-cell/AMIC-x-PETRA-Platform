"""KIIS 백엔드(:8001) API 호출 래퍼 — 모듈 간 연계."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

KIIS_BASE_URL = getattr(settings, "KIIS_API_URL", "http://kiis-api:8001/api/v1")


class KIISClient:
    """KIIS(기업정보 조사 서비스) 클라이언트."""

    def __init__(self, base_url: str = KIIS_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_company(self, name: str) -> list[dict]:
        """회사명으로 DART 기업 검색."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/companies", params={"q": name})
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", data) if isinstance(data, dict) else data

    async def get_company_detail(self, corp_code: str) -> dict:
        """기업 상세 정보 조회."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/companies/{corp_code}")
            resp.raise_for_status()
            return resp.json()

    async def search_gps(self, query: str) -> list[dict]:
        """GP(운용사) 검색."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/kofia/gp", params={"search": query})
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", data) if isinstance(data, dict) else data


kiis_client = KIISClient()
