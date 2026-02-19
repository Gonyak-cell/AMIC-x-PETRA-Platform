"""IM 백엔드(:8002) API 호출 래퍼 — 모듈 간 연계."""

from __future__ import annotations

import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

IM_BASE_URL = getattr(settings, "IM_API_URL", "http://im-api:8002/api/v1")


class IMClient:
    """IM(Information Memorandum) 서비스 클라이언트."""

    def __init__(self, base_url: str = IM_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_document(
        self, company_name: str, project_name: str, corp_code: str | None = None
    ) -> dict:
        """IM Document(CIM) 생성 요청."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload: dict = {
                "company_name": company_name,
                "project_name": project_name,
            }
            if corp_code:
                payload["corp_code"] = corp_code
            resp = await client.post(f"{self.base_url}/documents", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def get_document_status(self, document_id: uuid.UUID) -> dict:
        """CIM 생성 상태 조회."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/documents/{document_id}")
            resp.raise_for_status()
            return resp.json()

    async def trigger_generation(self, document_id: uuid.UUID) -> dict:
        """CIM 재생성 트리거."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/documents/{document_id}/regenerate"
            )
            resp.raise_for_status()
            return resp.json()


im_client = IMClient()
