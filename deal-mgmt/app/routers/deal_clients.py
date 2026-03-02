"""Deal Clients — 외부 고객의 딜 접근 배정 관리."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, require_role
from app.models.deal_client import DealClient
from app.models.enums import AuditAction
from app.schemas.deal_client import ClientDealSummary, DealClientCreate, DealClientOut
from app.services import audit_service, transaction_service

router = APIRouter(
    prefix="/transactions/{txn_id}/clients",
    tags=["Deal Clients"],
)

_MANAGE_ROLES = require_role("ADMIN", "MANAGER")


@router.get("", response_model=list[DealClientOut])
async def list_deal_clients(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_MANAGE_ROLES),
):
    """딜에 배정된 외부 고객 목록을 반환한다."""
    await transaction_service.get_transaction(db, txn_id)  # 404 체크
    result = await db.execute(
        select(DealClient).where(DealClient.transaction_id == txn_id).order_by(DealClient.created_at)
    )
    return [DealClientOut.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=DealClientOut, status_code=201)
async def assign_deal_client(
    txn_id: uuid.UUID,
    body: DealClientCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_MANAGE_ROLES),
):
    """외부 고객을 딜에 배정한다."""
    await transaction_service.get_transaction(db, txn_id)  # 404 체크

    # 중복 체크
    existing = await db.execute(
        select(DealClient.id).where(
            DealClient.transaction_id == txn_id,
            DealClient.email == body.email,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{body.email}'은(는) 이미 이 딜에 배정되어 있습니다",
        )

    dc = DealClient(
        transaction_id=txn_id,
        email=body.email,
        display_name=body.display_name,
        organization=body.organization,
        added_by_email=claims.email,
    )
    db.add(dc)

    await audit_service.record(
        db,
        entity_type="DealClient",
        entity_id=dc.id,
        action=AuditAction.CLIENT_ASSIGNED,
        actor_email=claims.email,
        new_value={"email": body.email, "transaction_id": txn_id},
    )

    await db.commit()
    await db.refresh(dc)
    return DealClientOut.model_validate(dc)


@router.delete("/{client_id}", status_code=204)
async def remove_deal_client(
    txn_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_MANAGE_ROLES),
):
    """외부 고객의 딜 배정을 제거한다."""
    result = await db.execute(
        select(DealClient).where(
            DealClient.id == client_id,
            DealClient.transaction_id == txn_id,
        )
    )
    dc = result.scalar_one_or_none()
    if dc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="배정 정보를 찾을 수 없습니다",
        )

    await audit_service.record(
        db,
        entity_type="DealClient",
        entity_id=dc.id,
        action=AuditAction.CLIENT_REMOVED,
        actor_email=claims.email,
        old_value={"email": dc.email, "transaction_id": txn_id},
    )

    await db.execute(delete(DealClient).where(DealClient.id == client_id))
    await db.commit()


# ── 관리자용 크로스-거래 라우터 ──────────────────────────────

admin_router = APIRouter(prefix="/deal-clients", tags=["Deal Clients"])


@admin_router.get("/by-email", response_model=list[ClientDealSummary])
async def get_deals_by_client_email(
    email: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(_MANAGE_ROLES),
):
    """특정 이메일로 배정된 모든 딜을 반환한다 (관리자용)."""
    from app.models.transaction import Transaction

    result = await db.execute(
        select(DealClient, Transaction.name, Transaction.code_name)
        .join(Transaction, DealClient.transaction_id == Transaction.id)
        .where(DealClient.email == email)
        .order_by(DealClient.created_at.desc())
    )
    return [
        ClientDealSummary(
            id=dc.id,
            transaction_id=dc.transaction_id,
            transaction_name=name,
            codename=codename or "",
            created_at=dc.created_at,
        )
        for dc, name, codename in result.all()
    ]
