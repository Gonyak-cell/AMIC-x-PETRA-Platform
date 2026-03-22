"""Workflow state machine for the 8-phase MA process."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowError
from app.core.log_decorators import log_error_with_input
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalType, AuditAction, TransactionPhase, TransactionStatus
from app.models.enums import TransactionPhase as Phase
from app.models.timeline import DealTimeline
from app.models.transaction import Transaction
from app.schemas.workflow import PhaseCompletionStatus
from app.services import audit_service

_PHASE_ORDER: list[TransactionPhase] = [
    Phase.ENGAGEMENT,
    Phase.PREPARATION,
    Phase.MARKETING,
    Phase.BIDDING,
    Phase.MAIN_DUE_DILIGENCE,
    Phase.NEGOTIATION,
    Phase.CLOSING,
    Phase.POST_CLOSING,
]

_PHASE_INDEX: dict[TransactionPhase, int] = {phase: index for index, phase in enumerate(_PHASE_ORDER)}

_VALID_STATUS_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.DRAFT: {TransactionStatus.ACTIVE, TransactionStatus.TERMINATED},
    TransactionStatus.ACTIVE: {TransactionStatus.ON_HOLD, TransactionStatus.COMPLETED, TransactionStatus.TERMINATED},
    TransactionStatus.ON_HOLD: {TransactionStatus.ACTIVE, TransactionStatus.TERMINATED},
    TransactionStatus.COMPLETED: set(),
    TransactionStatus.TERMINATED: set(),
}


async def get_phase_completion(db: AsyncSession, txn: Transaction) -> PhaseCompletionStatus:
    """Return simplified phase status without prerequisite hurdles."""
    _ = db
    idx = _PHASE_INDEX.get(txn.phase)
    if idx is None:
        raise WorkflowError(f"지원되지 않는 단계입니다: {txn.phase}")

    next_phase = _PHASE_ORDER[idx + 1] if idx < len(_PHASE_ORDER) - 1 else None
    previous_phase = _PHASE_ORDER[idx - 1] if idx > 0 else None
    can_advance = next_phase is not None and txn.status == TransactionStatus.ACTIVE

    blocking_reasons: list[str] = []
    if next_phase is None:
        blocking_reasons.append("마지막 단계입니다.")
    elif txn.status != TransactionStatus.ACTIVE:
        blocking_reasons.append(f"거래 상태가 {txn.status.value}입니다. ACTIVE 상태에서만 이동할 수 있습니다.")

    return PhaseCompletionStatus(
        current_phase=txn.phase,
        prerequisites=[],
        all_met=True,
        can_advance=can_advance,
        blocking_reasons=blocking_reasons,
        next_phase=next_phase,
        previous_phase=previous_phase,
        gate_summary=None,
        pending_acknowledgements=[],
        requires_user_acknowledgement=False,
    )


@log_error_with_input
async def advance_phase(
    db: AsyncSession,
    txn: Transaction,
    to_phase: TransactionPhase,
    actor_email: str | None = None,
    notes: str | None = None,
    acknowledgements: dict[str, bool] | None = None,
) -> Transaction:
    """Advance or roll back exactly one adjacent phase."""
    if txn.status != TransactionStatus.ACTIVE:
        raise WorkflowError("ACTIVE 상태의 거래만 단계 전환할 수 있습니다.")

    from_idx = _PHASE_INDEX.get(txn.phase)
    if from_idx is None:
        raise WorkflowError(f"지원되지 않는 단계입니다: {txn.phase}")

    to_idx = _PHASE_INDEX.get(to_phase)
    if to_idx is None:
        raise WorkflowError(f"잘못된 대상 단계입니다: {to_phase}")

    diff = to_idx - from_idx
    if diff not in (1, -1):
        raise WorkflowError(
            f"{txn.phase.value} -> {to_phase.value} 전환은 허용되지 않습니다. 인접 단계로만 이동할 수 있습니다."
        )

    from_phase = txn.phase
    txn.phase = to_phase

    event = DealTimeline(
        transaction_id=txn.id,
        event_type="PHASE_TRANSITION",
        title=f"{from_phase.value} -> {to_phase.value}",
        description=notes,
        event_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        is_auto_generated=True,
        created_by=actor_email,
    )
    db.add(event)

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.PHASE_TRANSITION,
        actor_email=actor_email,
        old_value={"phase": from_phase},
        new_value={"phase": to_phase, "acknowledgements": acknowledgements or None},
        notes=notes,
    )
    await db.commit()
    await db.refresh(txn)
    return txn


async def request_phase_approval(
    db: AsyncSession,
    txn: Transaction,
    to_phase: TransactionPhase,
    approver_emails: list[str],
    actor_email: str | None = None,
    notes: str | None = None,
) -> ApprovalRequest:
    """Create an approval request for moving to the next phase."""
    if txn.status != TransactionStatus.ACTIVE:
        raise WorkflowError("ACTIVE 상태의 거래만 승인 요청할 수 있습니다.")

    from_idx = _PHASE_INDEX.get(txn.phase)
    if from_idx is None:
        raise WorkflowError(f"지원되지 않는 단계입니다: {txn.phase}")

    to_idx = _PHASE_INDEX.get(to_phase)
    if to_idx is None or (to_idx - from_idx) != 1:
        raise WorkflowError(f"{txn.phase.value} -> {to_phase.value} 단계 전환에 대한 승인 요청은 허용되지 않습니다.")

    approvers = [
        {"email": email, "role": "APPROVER", "status": "PENDING", "comment": None, "decided_at": None}
        for email in approver_emails
    ]

    approval = ApprovalRequest(
        transaction_id=txn.id,
        requester_email=actor_email or "",
        approval_type=ApprovalType.PHASE_ADVANCE,
        title=f"단계 전환 승인: {txn.phase.value} -> {to_phase.value}",
        description=notes,
        approvers=approvers,
        related_entity_type="Transaction",
        related_entity_id=txn.id,
    )
    db.add(approval)
    await db.flush()

    await audit_service.record(
        db,
        entity_type="ApprovalRequest",
        entity_id=approval.id,
        action=AuditAction.APPROVAL_REQUESTED,
        actor_email=actor_email,
        new_value={"from_phase": txn.phase, "to_phase": to_phase},
    )
    await db.commit()
    await db.refresh(approval)
    return approval


async def change_status(
    db: AsyncSession,
    txn: Transaction,
    to_status: TransactionStatus,
    actor_email: str | None = None,
    reason: str | None = None,
) -> Transaction:
    """Change transaction status."""
    valid = _VALID_STATUS_TRANSITIONS.get(txn.status, set())
    if to_status not in valid:
        raise WorkflowError(f"{txn.status.value} -> {to_status.value} 상태 전환은 허용되지 않습니다.")

    from_status = txn.status
    txn.status = to_status

    event = DealTimeline(
        transaction_id=txn.id,
        event_type="STATUS_CHANGE",
        title=f"상태 변경: {from_status.value} -> {to_status.value}",
        description=reason,
        event_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        is_auto_generated=True,
        created_by=actor_email,
    )
    db.add(event)

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.STATUS_CHANGE,
        actor_email=actor_email,
        old_value={"status": from_status},
        new_value={"status": to_status},
        notes=reason,
    )
    await db.commit()
    await db.refresh(txn)
    return txn
