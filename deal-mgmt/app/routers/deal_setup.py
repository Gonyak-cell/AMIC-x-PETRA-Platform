"""딜 셋업 AI 에이전트 — 라우터.

POST /transactions/ai-setup           → 자연어 → DealSetupPreview
POST /transactions/ai-setup/excel     → 엑셀 → DealSetupPreview
POST /transactions/ai-setup/confirm   → 확인 → DB 저장 → DealSetupResult
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, require_write_access
from app.ralph.llm_client import RalphLLMClient
from app.schemas.deal_setup import (
    DealSetupConfirm,
    DealSetupPreview,
    DealSetupRequest,
    DealSetupResult,
)
from app.services import deal_setup_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/ai-setup", tags=["Deal Setup AI"])


def _get_llm_client() -> RalphLLMClient:
    """RalphLLMClient 인스턴스를 생성한다."""
    from app.core.config import settings

    return RalphLLMClient.from_settings(settings)


@router.post("", response_model=DealSetupPreview)
async def ai_setup_from_text(
    body: DealSetupRequest,
    claims: JWTClaims = Depends(require_write_access()),
) -> DealSetupPreview:
    """자연어 설명으로 딜 구조 미리보기를 생성한다."""
    llm_client = _get_llm_client()
    if not llm_client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 프로바이더를 사용할 수 없습니다",
        )
    try:
        return await deal_setup_service.generate_deal_setup_preview(body.description, llm_client=llm_client)
    except Exception as exc:
        logger.exception("딜 셋업 AI 미리보기 실패: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI 분석에 실패했습니다: {exc}",
        ) from exc


@router.post("/excel", response_model=DealSetupPreview)
async def ai_setup_from_excel(
    file: UploadFile,
    claims: JWTClaims = Depends(require_write_access()),
) -> DealSetupPreview:
    """엑셀 파일을 파싱하여 딜 구조 미리보기를 생성한다."""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다",
        )
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 크기는 10MB 이하여야 합니다",
        )

    llm_client = _get_llm_client()
    if not llm_client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 프로바이더를 사용할 수 없습니다",
        )
    try:
        return await deal_setup_service.generate_deal_setup_from_excel(file_bytes, llm_client=llm_client)
    except Exception as exc:
        logger.exception("딜 셋업 AI 엑셀 분석 실패: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"엑셀 AI 분석에 실패했습니다: {exc}",
        ) from exc


@router.post("/confirm", response_model=DealSetupResult, status_code=status.HTTP_201_CREATED)
async def ai_setup_confirm(
    body: DealSetupConfirm,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> DealSetupResult:
    """미리보기 확인 → DB에 벌크 저장."""
    return await deal_setup_service.confirm_deal_setup(db, body, actor_email=claims.email or "unknown")
