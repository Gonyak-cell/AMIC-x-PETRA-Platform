"""IOI/LOI/최종제안 관리 + 비교 매트릭스 라우터."""

from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.attachment import Attachment
from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction
from app.schemas.bid import (
    BidComparisonItem,
    BidCreate,
    BidImportRequest,
    BidImportResult,
    BidOut,
    BidUpdate,
)
from app.services import audit_service, bid_import_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/bids", tags=["Bids"])


@router.get("", response_model=list[BidOut])
async def list_bids(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID | None = None,
    bid_type: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(Bid).where(Bid.transaction_id == txn_id)
    if buyer_id:
        q = q.where(Bid.buyer_candidate_id == buyer_id)
    if bid_type:
        q = q.where(Bid.bid_type == bid_type)
    q = q.order_by(Bid.created_at.desc())
    result = await db.execute(q)
    return [BidOut.model_validate(b) for b in result.scalars().all()]


@router.get("/comparison", response_model=list[BidComparisonItem])
async def bid_comparison_matrix(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """매수자별 IOI/LOI/최종제안 비교 매트릭스."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # 모든 매수자
    buyers_q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id)
    buyers = list((await db.execute(buyers_q)).scalars().all())

    # 모든 Bid
    bids_q = select(Bid).where(Bid.transaction_id == txn_id).order_by(Bid.created_at.desc())
    bids = list((await db.execute(bids_q)).scalars().all())

    # 매수자별 최신 Bid 그룹화
    buyer_bids: dict[uuid.UUID, dict[str, Bid]] = defaultdict(dict)
    for bid in bids:
        bt = bid.bid_type.value
        if bt not in buyer_bids[bid.buyer_candidate_id]:
            buyer_bids[bid.buyer_candidate_id][bt] = bid

    result = []
    for buyer in buyers:
        bids_map = buyer_bids.get(buyer.id, {})
        result.append(
            BidComparisonItem(
                buyer_id=buyer.id,
                buyer_name=buyer.company_name,
                buyer_type=buyer.buyer_type.value,
                ioi=BidOut.model_validate(bids_map["IOI"]) if "IOI" in bids_map else None,
                loi=BidOut.model_validate(bids_map["LOI"]) if "LOI" in bids_map else None,
                final_offer=BidOut.model_validate(bids_map["FINAL_OFFER"]) if "FINAL_OFFER" in bids_map else None,
            )
        )

    return result


@router.post("", response_model=BidOut, status_code=201)
async def create_bid(
    txn_id: uuid.UUID,
    body: BidCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    payload = body.model_dump()
    bid = Bid(transaction_id=txn_id, **payload)
    db.add(bid)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="Bid",
        entity_id=bid.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await bid_import_service.sync_buyer_bid_snapshot(db, txn_id, bid.buyer_candidate_id)
    await db.commit()
    await db.refresh(bid)
    return BidOut.model_validate(bid)


@router.patch("/{bid_id}", response_model=BidOut)
async def update_bid(
    txn_id: uuid.UUID,
    bid_id: uuid.UUID,
    body: BidUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(Bid).where(Bid.id == bid_id, Bid.transaction_id == txn_id)
    bid = (await db.execute(q)).scalar_one_or_none()
    if bid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="입찰을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(bid, k) for k in update_data}
    for k, v in update_data.items():
        setattr(bid, k, v)
    await audit_service.record(
        db,
        entity_type="Bid",
        entity_id=bid.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await bid_import_service.sync_buyer_bid_snapshot(db, txn_id, bid.buyer_candidate_id)
    await db.commit()
    await db.refresh(bid)
    return BidOut.model_validate(bid)


@router.delete("/{bid_id}", status_code=204)
async def delete_bid(
    txn_id: uuid.UUID,
    bid_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(Bid).where(Bid.id == bid_id, Bid.transaction_id == txn_id)
    bid = (await db.execute(q)).scalar_one_or_none()
    if bid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="입찰을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="Bid",
        entity_id=bid.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    buyer_candidate_id = bid.buyer_candidate_id
    await db.delete(bid)
    await bid_import_service.sync_buyer_bid_snapshot(db, txn_id, buyer_candidate_id)
    await db.commit()


@router.post("/import-from-attachment", response_model=BidImportResult)
async def import_bid_from_attachment(
    txn_id: uuid.UUID,
    body: BidImportRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    attachment = (
        await db.execute(
            select(Attachment).where(
                Attachment.transaction_id == txn_id,
                Attachment.id == body.attachment_id,
            )
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="첨부 파일을 찾을 수 없습니다.",
        )
    if attachment.entity_type != "BID":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="입찰 문서만 자동 기재에 사용할 수 있습니다.",
        )

    try:
        analysis = await bid_import_service.analyze_bid_attachment(
            db,
            txn_id,
            attachment,
            buyer_candidate_id=body.buyer_candidate_id,
            bid_type=body.bid_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    existing_bid = await bid_import_service.find_bid_import_target(
        db,
        txn_id,
        analysis.buyer.id,
        analysis.bid_type,
    )

    created = existing_bid is None
    updated_fields: list[str] = []
    if created:
        bid = Bid(
            transaction_id=txn_id,
            buyer_candidate_id=analysis.buyer.id,
            bid_type=analysis.bid_type,
            amount=analysis.amount,
            currency=analysis.currency,
            valuation_method=analysis.valuation_method,
            multiple=analysis.multiple,
            submitted_at=analysis.submitted_at,
            valid_until=analysis.valid_until,
            notes=f"Imported from attachment: {attachment.file_name}",
        )
        db.add(bid)
        await db.flush()
        await audit_service.record(
            db,
            entity_type="Bid",
            entity_id=bid.id,
            action=AuditAction.CREATE,
            actor_email=claims.email,
            new_value={
                "buyer_candidate_id": str(analysis.buyer.id),
                "bid_type": analysis.bid_type.value,
                "amount": str(analysis.amount) if analysis.amount is not None else None,
                "currency": analysis.currency,
                "valuation_method": analysis.valuation_method.value if analysis.valuation_method is not None else None,
                "multiple": str(analysis.multiple) if analysis.multiple is not None else None,
                "submitted_at": analysis.submitted_at,
                "valid_until": analysis.valid_until,
                "notes": f"Imported from attachment: {attachment.file_name}",
                "attachment_id": str(attachment.id),
            },
        )
    else:
        bid = existing_bid
        old_value, update_data = bid_import_service.apply_analysis_to_bid(bid, analysis)
        attachment_note = f"Imported from attachment: {attachment.file_name}"
        if not bid.notes:
            bid.notes = attachment_note
        updated_fields = list(update_data.keys())
        if updated_fields:
            await audit_service.record(
                db,
                entity_type="Bid",
                entity_id=bid.id,
                action=AuditAction.UPDATE,
                actor_email=claims.email,
                old_value=old_value,
                new_value={
                    key: value.value
                    if hasattr(value, "value")
                    else str(value)
                    if isinstance(value, uuid.UUID)
                    else value
                    for key, value in update_data.items()
                },
            )

    attachment.entity_id = str(bid.id)
    await bid_import_service.sync_buyer_bid_snapshot(db, txn_id, analysis.buyer.id)
    await db.commit()
    await db.refresh(bid)
    await db.refresh(attachment)

    return BidImportResult(
        bid=BidOut.model_validate(bid),
        attachment_id=attachment.id,
        attachment_file_name=attachment.file_name,
        buyer_name=analysis.buyer.company_name,
        created=created,
        inferred_fields=analysis.inferred_fields,
        updated_fields=updated_fields,
        warnings=analysis.warnings,
    )
