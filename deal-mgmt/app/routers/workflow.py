"""8단계 워크플로우 상태 머신 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.schemas.transaction import TransactionOut
from app.schemas.workflow import (
    PhaseCompletionStatus,
    PhaseTransitionRequest,
    StatusChangeRequest,
)
from app.services import transaction_service
from app.services.workflow import advance_phase, change_status, get_phase_completion

router = APIRouter(prefix="/transactions/{txn_id}/workflow", tags=["Workflow"])


@router.get("/phase-status", response_model=PhaseCompletionStatus)
async def get_phase_status(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """현재 단계의 완료 조건 및 전환 가능 여부를 확인한다."""
    txn = await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return await get_phase_completion(db, txn)


@router.post("/advance", response_model=TransactionOut)
async def advance_transaction_phase(
    txn_id: uuid.UUID,
    body: PhaseTransitionRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """다음/이전 단계로 전환한다."""
    txn = await transaction_service.get_transaction(db, txn_id)
    updated = await advance_phase(
        db,
        txn,
        body.to_phase,
        actor_email=claims.email,
        notes=body.notes,
        acknowledgements=body.acknowledgements,
    )
    return TransactionOut.model_validate(updated)


@router.post("/status", response_model=TransactionOut)
async def change_transaction_status(
    txn_id: uuid.UUID,
    body: StatusChangeRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """거래 상태를 변경한다 (DRAFT → ACTIVE → ON_HOLD/COMPLETED/TERMINATED)."""
    txn = await transaction_service.get_transaction(db, txn_id)
    updated = await change_status(db, txn, body.to_status, actor_email=claims.email, reason=body.reason)
    return TransactionOut.model_validate(updated)
