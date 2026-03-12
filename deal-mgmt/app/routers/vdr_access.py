"""VDR 접근 추적 전용 라우터 — access logs, activity summary."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.enums import VdrAccessAction
from app.routers.vdr import _get_and_authorize_txn
from app.schemas.vdr import (
    BuyerActivitySummary,
    VdrAccessLogListResponse,
    VdrAccessLogOut,
)
from app.services import vdr_access_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/vdr",
    tags=["VDR Access"],
)


@router.get("/access-logs", response_model=VdrAccessLogListResponse)
async def get_access_logs(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID | None = Query(None),
    document_id: uuid.UUID | None = Query(None),
    action: VdrAccessAction | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> VdrAccessLogListResponse:
    """VDR 전체 접근 로그 조회 (필터 가능)."""
    await _get_and_authorize_txn(db, txn_id, claims)
    logs, total = await vdr_access_service.get_access_logs(
        db,
        txn_id,
        buyer_id=buyer_id,
        document_id=document_id,
        action=action,
        skip=skip,
        limit=limit,
    )
    return VdrAccessLogListResponse(
        items=[VdrAccessLogOut.model_validate(log) for log in logs],
        total=total,
    )


@router.get("/access-summary", response_model=list[BuyerActivitySummary])
async def get_access_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[BuyerActivitySummary]:
    """매수자별 VDR 활동 요약."""
    await _get_and_authorize_txn(db, txn_id, claims)
    summaries = await vdr_access_service.get_buyer_activity_summary(db, txn_id)
    return [BuyerActivitySummary(**s) for s in summaries]


@router.get("/documents/{doc_id}/access-logs", response_model=VdrAccessLogListResponse)
async def get_document_access_logs(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> VdrAccessLogListResponse:
    """특정 문서의 접근 이력 조회."""
    await _get_and_authorize_txn(db, txn_id, claims)
    logs, total = await vdr_access_service.get_document_access_logs(
        db,
        txn_id,
        doc_id,
        skip=skip,
        limit=limit,
    )
    return VdrAccessLogListResponse(
        items=[VdrAccessLogOut.model_validate(log) for log in logs],
        total=total,
    )
