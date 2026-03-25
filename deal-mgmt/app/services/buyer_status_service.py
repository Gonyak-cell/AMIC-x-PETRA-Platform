"""Buyer status auto-advance and shortlist sync helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, BuyerCandidateStatus, BuyerTier, MarketingStage, NdaPartyType, NdaStatus
from app.models.nda import NDA
from app.services import audit_service

_S = BuyerCandidateStatus

MARKETING_STATUS_ADVANCE: dict[MarketingStage, BuyerCandidateStatus] = {
    MarketingStage.TEASER_SENT: _S.CONTACTED,
    MarketingStage.NDA_SIGNED: _S.NDA_SIGNED,
    MarketingStage.IM_DISTRIBUTED: _S.CIM_SENT,
    MarketingStage.LOI_RECEIVED: _S.LOI_RECEIVED,
    MarketingStage.DD_IN_PROGRESS: _S.DD_IN_PROGRESS,
}

# CONTACTED moves straight to NDA_SIGNED because the marketing log flow does not
# have a separate "NDA sent" milestone.
ADVANCE_PATH: dict[BuyerCandidateStatus, BuyerCandidateStatus] = {
    _S.IDENTIFIED: _S.CONTACTED,
    _S.CONTACTED: _S.NDA_SIGNED,
    _S.NDA_SENT: _S.NDA_SIGNED,
    _S.NDA_SIGNED: _S.CIM_SENT,
    _S.CIM_SENT: _S.INTEREST_CONFIRMED,
    _S.INTEREST_CONFIRMED: _S.IOI_RECEIVED,
    _S.IOI_RECEIVED: _S.IOI_ACCEPTED,
    _S.IOI_ACCEPTED: _S.DD_GRANTED,
    _S.DD_GRANTED: _S.DD_IN_PROGRESS,
    _S.DD_IN_PROGRESS: _S.LOI_RECEIVED,
    _S.LOI_RECEIVED: _S.LOI_ACCEPTED,
    _S.LOI_ACCEPTED: _S.SELECTED,
    _S.SELECTED: _S.BID_SUBMITTED,
}

STATUS_ORDER: dict[BuyerCandidateStatus, int] = {
    _S.IDENTIFIED: 0,
    _S.CONTACTED: 1,
    _S.NDA_SENT: 2,
    _S.NDA_SIGNED: 3,
    _S.CIM_SENT: 4,
    _S.INTEREST_CONFIRMED: 5,
    _S.IOI_RECEIVED: 6,
    _S.IOI_ACCEPTED: 7,
    _S.DD_GRANTED: 8,
    _S.DD_IN_PROGRESS: 9,
    _S.LOI_RECEIVED: 10,
    _S.LOI_ACCEPTED: 11,
    _S.SELECTED: 12,
    _S.BID_SUBMITTED: 13,
}

TERMINAL_STATUSES: frozenset[BuyerCandidateStatus] = frozenset(
    {
        _S.REJECTED,
        _S.BID_DROPPED,
        _S.BID_NOT_SUBMITTED,
    }
)

SHORT_LIST_TIERS: frozenset[BuyerTier] = frozenset(
    {
        BuyerTier.TIER_1,
        BuyerTier.TIER_2,
        BuyerTier.TIER_3,
    }
)
_SHORT_LIST_ENTRY_ORDINAL = STATUS_ORDER[_S.NDA_SIGNED]


def is_short_list_tier(tier: BuyerTier | None) -> bool:
    return tier in SHORT_LIST_TIERS


def has_short_list_entry_status(status: BuyerCandidateStatus) -> bool:
    ordinal = STATUS_ORDER.get(status)
    return ordinal is not None and ordinal >= _SHORT_LIST_ENTRY_ORDINAL


async def buyer_has_signed_nda(db: AsyncSession, buyer_id: uuid.UUID) -> bool:
    query = (
        select(NDA.id)
        .where(
            NDA.buyer_candidate_id == buyer_id,
            NDA.party_type == NdaPartyType.BUYER,
            NDA.status == NdaStatus.SIGNED,
        )
        .limit(1)
    )
    return (await db.execute(query)).scalar_one_or_none() is not None


async def derive_short_list_membership(
    db: AsyncSession,
    *,
    tier: BuyerTier | None,
    status: BuyerCandidateStatus,
    current_short_listed: bool = False,
    buyer_id: uuid.UUID | None = None,
    signed_nda: bool | None = None,
) -> bool:
    if not is_short_list_tier(tier):
        return False

    if has_short_list_entry_status(status):
        return True

    if signed_nda is not None:
        return signed_nda

    if buyer_id is None:
        return False

    return await buyer_has_signed_nda(db, buyer_id)


async def sync_short_list_membership(
    db: AsyncSession,
    buyer: BuyerCandidate,
    *,
    tier: BuyerTier | None = None,
    status: BuyerCandidateStatus | None = None,
    signed_nda: bool | None = None,
) -> bool:
    next_value = await derive_short_list_membership(
        db,
        tier=buyer.tier if tier is None else tier,
        status=buyer.status if status is None else status,
        current_short_listed=buyer.is_short_listed,
        buyer_id=buyer.id,
        signed_nda=signed_nda,
    )
    buyer.is_short_listed = next_value
    return next_value


async def sync_transaction_short_list_memberships(
    db: AsyncSession,
    txn_id: uuid.UUID,
) -> None:
    buyers = (
        (
            await db.execute(
                select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id),
            )
        )
        .scalars()
        .all()
    )

    changed = False
    for buyer in buyers:
        previous = buyer.is_short_listed
        next_value = await sync_short_list_membership(db, buyer)
        if previous != next_value:
            changed = True

    if changed:
        await db.flush()


async def auto_advance_buyer_status(
    db: AsyncSession,
    buyer: BuyerCandidate,
    target: BuyerCandidateStatus,
    actor_email: str,
) -> None:
    """Advance buyer.status toward target when the request moves forward."""
    if buyer.status in TERMINAL_STATUSES:
        await sync_short_list_membership(db, buyer, signed_nda=False)
        return

    cur_ord = STATUS_ORDER.get(buyer.status)
    tgt_ord = STATUS_ORDER.get(target)
    if cur_ord is None or tgt_ord is None or cur_ord >= tgt_ord:
        await sync_short_list_membership(db, buyer, signed_nda=False)
        return

    visited: set[BuyerCandidateStatus] = set()
    while STATUS_ORDER.get(buyer.status, 99) < tgt_ord:
        if buyer.status in visited:
            break
        visited.add(buyer.status)
        next_status = ADVANCE_PATH.get(buyer.status)
        if next_status is None:
            break
        old = buyer.status
        buyer.status = next_status
        await audit_service.record(
            db,
            entity_type="BuyerCandidate",
            entity_id=buyer.id,
            action=AuditAction.STATUS_CHANGE,
            actor_email=actor_email,
            old_value={"status": old.value},
            new_value={"status": next_status.value},
            notes="Marketing-stage auto advance",
        )

    await sync_short_list_membership(db, buyer, signed_nda=False)


def get_advance_target(stage: MarketingStage) -> BuyerCandidateStatus | None:
    return MARKETING_STATUS_ADVANCE.get(stage)


def has_advance_mapping(stage: MarketingStage) -> bool:
    return stage in MARKETING_STATUS_ADVANCE


async def check_status_after_delete(
    db: AsyncSession,
    buyer_id: uuid.UUID,
    deleted_stage: MarketingStage,
    actor_email: str,
) -> None:
    """Log that manual buyer status review may be needed after log deletion."""
    if not has_advance_mapping(deleted_stage):
        return

    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer_id,
        action=AuditAction.STATUS_CHANGE,
        actor_email=actor_email,
        notes=(
            f"Marketing log deleted (stage={deleted_stage.value}). "
            "Review buyer.status manually because auto-advance history changed."
        ),
    )
