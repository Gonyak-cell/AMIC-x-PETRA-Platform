"""매수자 상태 자동 승격 서비스 — 마케팅 스테이지 기반."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, BuyerCandidateStatus, MarketingStage
from app.services import audit_service

logger = logging.getLogger(__name__)

_S = BuyerCandidateStatus

# 마케팅 스테이지 → 목표 buyer status 매핑
MARKETING_STATUS_ADVANCE: dict[MarketingStage, BuyerCandidateStatus] = {
    MarketingStage.TEASER_SENT: _S.CONTACTED,
    MarketingStage.NDA_SIGNED: _S.NDA_SIGNED,
    MarketingStage.IM_DISTRIBUTED: _S.CIM_SENT,
    MarketingStage.LOI_RECEIVED: _S.LOI_RECEIVED,
    MarketingStage.DD_IN_PROGRESS: _S.DD_IN_PROGRESS,
}

# 선형 승격 경로 (중간 상태를 순차적으로 통과)
# NOTE: CONTACTED → NDA_SIGNED은 의도적으로 NDA_SENT를 건너뜀.
# 마케팅 스테이지에 "NDA 발송" 단계가 없으므로 자동 승격 시 NDA_SENT를 경유하지 않는다.
# NDA_SENT 상태의 buyer가 있는 경우를 위해 NDA_SENT → NDA_SIGNED 경로는 별도 유지.
ADVANCE_PATH: dict[BuyerCandidateStatus, BuyerCandidateStatus] = {
    _S.IDENTIFIED: _S.CONTACTED,
    _S.CONTACTED: _S.NDA_SIGNED,
    _S.NDA_SENT: _S.NDA_SIGNED,
    _S.NDA_SIGNED: _S.CIM_SENT,
    _S.CIM_SENT: _S.INTEREST_CONFIRMED,
    _S.INTEREST_CONFIRMED: _S.IOI_RECEIVED,
    _S.IOI_RECEIVED: _S.IOI_ACCEPTED,
    _S.IOI_ACCEPTED: _S.DD_GRANTED,
}

# 순서 판정용 ordinal (터미널 상태 제외)
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


async def auto_advance_buyer_status(
    db: AsyncSession,
    buyer: BuyerCandidate,
    target: BuyerCandidateStatus,
    actor_email: str,
) -> None:
    """buyer.status를 target까지 순차 승격. 이미 같거나 높으면 무시."""
    # 터미널 상태(REJECTED, BID_DROPPED 등)는 승격하지 않음
    if buyer.status in TERMINAL_STATUSES:
        return

    cur_ord = STATUS_ORDER.get(buyer.status)
    tgt_ord = STATUS_ORDER.get(target)
    if cur_ord is None or tgt_ord is None or cur_ord >= tgt_ord:
        return

    visited: set[BuyerCandidateStatus] = set()
    while STATUS_ORDER.get(buyer.status, 99) < tgt_ord:
        if buyer.status in visited:
            break  # 순환 방지
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
            notes="마케팅 스테이지 기반 자동 승격",
        )


def get_advance_target(stage: MarketingStage) -> BuyerCandidateStatus | None:
    """마케팅 스테이지에 대응하는 목표 buyer status를 반환한다."""
    return MARKETING_STATUS_ADVANCE.get(stage)


def has_advance_mapping(stage: MarketingStage) -> bool:
    """해당 마케팅 스테이지가 자동 승격 매핑을 가지는지 반환한다."""
    return stage in MARKETING_STATUS_ADVANCE


async def check_status_after_delete(
    db: AsyncSession,
    buyer_id: uuid.UUID,
    deleted_stage: MarketingStage,
    actor_email: str,
) -> None:
    """마케팅 로그 삭제 후, 자동 승격에 영향을 줄 수 있음을 감사 로그에 기록한다.

    buyer.status 롤백은 수행하지 않는다 (안전한 롤백 대상 결정이 어려움).
    대신 감사 로그에 경고를 남겨 수동 검토를 유도한다.
    """
    if not has_advance_mapping(deleted_stage):
        return

    await audit_service.record(
        db,
        entity_type="BuyerCandidate",
        entity_id=buyer_id,
        action=AuditAction.STATUS_CHANGE,
        actor_email=actor_email,
        notes=(
            f"마케팅 로그 삭제됨 (stage={deleted_stage.value}). "
            "이 스테이지는 자동 승격 트리거였으므로 buyer.status 수동 검토 필요."
        ),
    )
