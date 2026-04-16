"""FDD 백엔드(:8000) API 호출 래퍼 — 모듈 간 연계."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

FDD_BASE_URL = getattr(settings, "FDD_API_URL", "http://fdd-api:8000/api/v1")
FDD_EVIDENCE_EXPORT_PATH_TEMPLATE = getattr(
    settings,
    "FDD_EVIDENCE_EXPORT_PATH_TEMPLATE",
    "/deals/{deal_id}/evidence-export",
)
_NON_FALLBACK_ENV_NAMES = {"prod", "production", "stg", "staging"}
_SUPPORTED_FDD_INDUSTRIES = {
    "general",
    "tech",
    "healthcare",
    "manufacturing",
    "financial_services",
    "logistics",
}


def _local_fallback_enabled() -> bool:
    env = os.getenv("ENV", "").strip().lower()
    return env not in _NON_FALLBACK_ENV_NAMES or bool(getattr(settings, "DEBUG", False))


def _normalize_fdd_industry(industry: str | None) -> str:
    normalized = (industry or "general").strip().lower()
    return normalized if normalized in _SUPPORTED_FDD_INDUSTRIES else "general"


class FDDClient:
    """FDD 서비스 클라이언트 — 커넥션 풀 재사용."""

    def __init__(self, base_url: str = FDD_BASE_URL, timeout: float = 10.0):
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

    async def create_deal(self, target_name: str, industry: str | None = None) -> dict:
        """FDD Deal 생성 요청."""
        client = await self._get_client()
        try:
            resp = await client.post(
                "/deals",
                json={
                    "name": target_name,
                    "target_company_name": target_name,
                    "industry": _normalize_fdd_industry(industry),
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if not _local_fallback_enabled():
                raise
            fallback_id = uuid.uuid4()
            logger.warning("Using local FDD deal fallback for target=%s", target_name, exc_info=True)
            return {
                "id": str(fallback_id),
                "target_name": target_name,
                "industry": industry,
                "status": "LOCAL_FALLBACK",
            }

    async def get_deal_status(self, deal_id: uuid.UUID) -> dict:
        """FDD Deal 상태 조회 (QoE/NWC/Debt 분석 진행률)."""
        client = await self._get_client()
        try:
            resp = await client.get(f"/deals/{deal_id}/summary")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if not _local_fallback_enabled():
                raise
            logger.warning("Using local FDD status fallback for deal=%s", deal_id, exc_info=True)
            return {
                "id": str(deal_id),
                "status": "LOCAL_FALLBACK",
                "uploads": [],
                "analyses": [],
                "fallback": True,
            }

    async def get_evidence_export(self, deal_id: uuid.UUID) -> dict:
        """Fetch normalized evidence export payload from FDD."""
        client = await self._get_client()
        try:
            resp = await client.get(FDD_EVIDENCE_EXPORT_PATH_TEMPLATE.format(deal_id=deal_id))
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if not _local_fallback_enabled():
                raise
            logger.warning("Using local FDD evidence fallback for deal=%s", deal_id, exc_info=True)
            return {
                "artifact_type": "FDD_REPORT",
                "external_artifact_ref": f"fdd-{deal_id}",
                "default_workstream": "FDD",
                "records": [],
                "fallback": True,
            }

    async def trigger_analysis(self, deal_id: uuid.UUID, analysis_type: str) -> dict:
        """QoE/NWC/Debt 분석 트리거."""
        client = await self._get_client()
        try:
            resp = await client.post(
                f"/deals/{deal_id}/{analysis_type}/trigger",
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if not _local_fallback_enabled():
                raise
            logger.warning(
                "Using local FDD analysis trigger fallback for deal=%s analysis=%s",
                deal_id,
                analysis_type,
                exc_info=True,
            )
            return {
                "deal_id": str(deal_id),
                "analysis_type": analysis_type,
                "status": "LOCAL_FALLBACK_TRIGGERED",
                "fallback": True,
            }

    async def upload_file(
        self,
        deal_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict:
        client = await self._get_client()
        try:
            resp = await client.post(
                f"/deals/{deal_id}/uploads",
                files={"file": (filename, content, content_type)},
                timeout=300,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if not _local_fallback_enabled():
                raise
            upload_id = uuid.uuid4()
            logger.warning("Using local FDD upload fallback for deal=%s filename=%s", deal_id, filename, exc_info=True)
            return {
                "id": str(upload_id),
                "deal_id": str(deal_id),
                "original_filename": filename,
                "file_size_bytes": len(content),
                "status": "PENDING",
                "detected_type": None,
                "fallback": True,
            }

    async def ingest_upload(self, deal_id: uuid.UUID, upload_id: uuid.UUID) -> dict:
        client = await self._get_client()
        try:
            resp = await client.post(f"/deals/{deal_id}/uploads/{upload_id}/ingest", json={}, timeout=300)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if not _local_fallback_enabled():
                raise
            logger.warning("Using local FDD ingest fallback for deal=%s upload=%s", deal_id, upload_id, exc_info=True)
            return {
                "id": str(upload_id),
                "deal_id": str(deal_id),
                "status": "INGESTED",
                "fallback": True,
            }
