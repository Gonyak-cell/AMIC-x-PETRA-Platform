"""NDA management APIs for buyer and client counterparties."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, BuyerCandidateStatus, NdaPartyType, NdaStatus
from app.models.nda import NDA
from app.schemas.nda import NDACreate, NDAOut, NDASummary, NDAUpdate
from app.services import audit_service, transaction_service
from app.services.buyer_status_service import auto_advance_buyer_status, sync_short_list_membership

router = APIRouter(prefix="/transactions/{txn_id}/ndas", tags=["NDAs"])


def _normalized_counterparty_name(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _validate_nda_payload(
    *,
    transaction_client_name: str,
    party_type: NdaPartyType,
    buyer_candidate_id: uuid.UUID | None,
    counterparty_name: str | None,
) -> tuple[uuid.UUID | None, str | None]:
    if party_type == NdaPartyType.BUYER:
        if buyer_candidate_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="매수자 NDA에는 buyer_candidate_id가 필요합니다.",
            )
        return buyer_candidate_id, counterparty_name

    if buyer_candidate_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="클라이언트 NDA에는 buyer_candidate_id를 사용할 수 없습니다.",
        )

    return None, counterparty_name or transaction_client_name


@router.get("", response_model=list[NDAOut])
async def list_ndas(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID | None = None,
    party_type: NdaPartyType | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    query = select(NDA).where(NDA.transaction_id == txn_id)
    if buyer_id:
        query = query.where(NDA.buyer_candidate_id == buyer_id)
    if party_type:
        query = query.where(NDA.party_type == party_type)

    query = query.order_by(NDA.created_at.desc())
    result = await db.execute(query)
    return [NDAOut.model_validate(item) for item in result.scalars().all()]


@router.get("/summary", response_model=NDASummary)
async def nda_summary(
    txn_id: uuid.UUID,
    party_type: NdaPartyType | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    query = select(NDA).where(NDA.transaction_id == txn_id)
    if party_type:
        query = query.where(NDA.party_type == party_type)

    result = await db.execute(query)
    ndas = list(result.scalars().all())

    by_status: dict[str, int] = {}
    signed = 0
    pending = 0
    for nda in ndas:
        by_status[nda.status.value] = by_status.get(nda.status.value, 0) + 1
        if nda.status == NdaStatus.SIGNED:
            signed += 1
        elif nda.status in (NdaStatus.DRAFT, NdaStatus.SENT):
            pending += 1

    return NDASummary(
        total=len(ndas),
        by_status=by_status,
        signed_count=signed,
        pending_count=pending,
    )


@router.post("", response_model=NDAOut, status_code=201)
async def create_nda(
    txn_id: uuid.UUID,
    body: NDACreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    transaction = await transaction_service.get_transaction(db, txn_id)
    buyer_candidate_id, counterparty_name = _validate_nda_payload(
        transaction_client_name=transaction.client_name,
        party_type=body.party_type,
        buyer_candidate_id=body.buyer_candidate_id,
        counterparty_name=_normalized_counterparty_name(body.counterparty_name),
    )

    nda = NDA(
        transaction_id=txn_id,
        party_type=body.party_type,
        buyer_candidate_id=buyer_candidate_id,
        counterparty_name=counterparty_name,
        nda_type=body.nda_type,
        sent_at=body.sent_at,
        expires_at=body.expires_at,
        document_url=body.document_url,
        notes=body.notes,
    )
    db.add(nda)
    await db.flush()

    await audit_service.record(
        db,
        entity_type="NDA",
        entity_id=nda.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(nda)
    return NDAOut.model_validate(nda)


@router.patch("/{nda_id}", response_model=NDAOut)
async def update_nda(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    body: NDAUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    query = select(NDA).where(NDA.id == nda_id, NDA.transaction_id == txn_id)
    nda = (await db.execute(query)).scalar_one_or_none()
    if nda is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NDA를 찾을 수 없습니다.",
        )

    update_data = body.model_dump(exclude_unset=True)
    if "counterparty_name" in update_data:
        update_data["counterparty_name"] = _normalized_counterparty_name(
            update_data["counterparty_name"],
        )

    old_value = {key: getattr(nda, key) for key in update_data}
    for key, value in update_data.items():
        setattr(nda, key, value)

    if nda.party_type == NdaPartyType.BUYER and nda.buyer_candidate_id is not None and nda.status == NdaStatus.SIGNED:
        buyer = await db.get(BuyerCandidate, nda.buyer_candidate_id)
        if buyer is not None:
            await auto_advance_buyer_status(
                db,
                buyer,
                BuyerCandidateStatus.NDA_SIGNED,
                claims.email,
            )
            await sync_short_list_membership(db, buyer, signed_nda=True)

    await audit_service.record(
        db,
        entity_type="NDA",
        entity_id=nda.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(nda)
    return NDAOut.model_validate(nda)


@router.delete("/{nda_id}", status_code=204)
async def delete_nda(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    query = select(NDA).where(NDA.id == nda_id, NDA.transaction_id == txn_id)
    nda = (await db.execute(query)).scalar_one_or_none()
    if nda is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NDA를 찾을 수 없습니다.",
        )

    await audit_service.record(
        db,
        entity_type="NDA",
        entity_id=nda.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(nda)
    await db.commit()
