"""Transaction CRUD 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import TransactionPhase, TransactionSide, TransactionStatus
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdate,
)
from app.schemas.workspace_summary import WorkspaceSummary
from app.services import transaction_service, workspace_summary_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/{txn_id}/workspace-summary", response_model=WorkspaceSummary)
async def get_workspace_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> WorkspaceSummary:
    """워크스페이스 탭 배지 카운트 — 단일 쿼리로 13개 엔티티 집계."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return await workspace_summary_service.get_workspace_summary(db, txn_id)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    search: str | None = Query(None, description="이름/코드네임/대상/클라이언트 검색"),
    side: TransactionSide | None = Query(None, description="SELL, BUY, DUAL"),
    phase: TransactionPhase | None = Query(None, description="7단계 필터"),
    status: TransactionStatus | None = Query(None, description="DRAFT, ACTIVE, ON_HOLD, COMPLETED, TERMINATED"),
    assigned_to_me: bool = Query(False, description="내 담당 거래만 (lead_advisor 또는 deal_captain)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    client_email = claims.email if claims.role == "CLIENT" else None
    assigned_to_email = claims.email if assigned_to_me else None
    items, total = await transaction_service.list_transactions(
        db,
        search=search,
        side=side,
        phase=phase,
        tx_status=status,
        limit=limit,
        offset=offset,
        client_email=client_email,
        assigned_to_email=assigned_to_email,
    )
    return TransactionListResponse(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{txn_id}", response_model=TransactionOut)
async def get_transaction(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    txn = await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    return TransactionOut.model_validate(txn)


@router.post("", response_model=TransactionOut, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    from sqlalchemy.exc import IntegrityError

    try:
        txn = await transaction_service.create_transaction(db, body, actor_email=claims.email)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="코드명 생성 중 충돌이 발생했습니다. 다시 시도해 주세요.",
        )
    return TransactionOut.model_validate(txn)


@router.patch("/{txn_id}", response_model=TransactionOut)
async def update_transaction(
    txn_id: uuid.UUID,
    body: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    txn = await transaction_service.update_transaction(db, txn_id, body, actor_email=claims.email)
    return TransactionOut.model_validate(txn)


@router.delete("/{txn_id}", status_code=204)
async def delete_transaction(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.delete_transaction(db, txn_id, actor_email=claims.email)
