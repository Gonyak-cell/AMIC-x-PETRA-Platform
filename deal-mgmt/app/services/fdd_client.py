"""FDD 백엔드(:8000) API 호출 래퍼 — 모듈 간 연계."""

from __future__ import annotations

import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

FDD_BASE_URL = getattr(settings, "FDD_API_URL", "http://fdd-api:8000/api/v1")


class FDDClient:
    """FDD 서비스 클라이언트."""

    def __init__(self, base_url: str = FDD_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_deal(self, target_name: str, industry: str | None = None) -> dict:
        """FDD Deal 생성 요청."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/deals",
                json={"target_name": target_name, "industry": industry},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_deal_status(self, deal_id: uuid.UUID) -> dict:
        """FDD Deal 상태 조회 (QoE/NWC/Debt 분석 진행률)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/deals/{deal_id}/summary")
            resp.raise_for_status()
            return resp.json()

    async def trigger_analysis(self, deal_id: uuid.UUID, analysis_type: str) -> dict:
        """QoE/NWC/Debt 분석 트리거."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/deals/{deal_id}/{analysis_type}/trigger",
            )
            resp.raise_for_status()
            return resp.json()


fdd_client = FDDClient()
