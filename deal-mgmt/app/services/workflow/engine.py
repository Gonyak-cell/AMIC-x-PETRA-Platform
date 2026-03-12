"""8단계 M&A 워크플로우 상태 머신.

Phase 순서: ENGAGEMENT → PREPARATION → MARKETING → BIDDING → MAIN_DUE_DILIGENCE → NEGOTIATION → CLOSING → POST_CLOSING
전환 규칙: 한 단계 앞/뒤로만 이동 가능, 건너뛰기 불가.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowError
from app.core.log_decorators import log_error_with_input
from app.models.approval import ApprovalRequest
from app.models.enums import (
    ApprovalType,
    AuditAction,
    TransactionPhase,
    TransactionStatus,
)
from app.models.enums import TransactionPhase as Phase
from app.models.timeline import DealTimeline
from app.models.transaction import Transaction
from app.schemas.workflow import PhaseCompletionStatus, PhasePrerequisite
from app.services import audit_service
from app.services.workflow.validators import PHASE_GATE_SUMMARIES, PHASE_GATE_VALIDATORS

# 순서가 있는 8단계 (MOU_SIGNED는 마일스톤으로 전환, 독립 단계에서 제거)
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

_PHASE_INDEX: dict[TransactionPhase, int] = {p: i for i, p in enumerate(_PHASE_ORDER)}

# 단계별 전제 조건 — Transaction 필드 기반 (기존 호환 유지)
_PHASE_PREREQUISITES: dict[TransactionPhase, list[tuple[str, str]]] = {
    Phase.ENGAGEMENT: [],
    Phase.PREPARATION: [
        ("client_name", "클라이언트 정보"),
        ("lead_advisor_email", "리드 어드바이저"),
    ],
    Phase.MARKETING: [
        ("target_company_name", "대상 기업 정보"),
    ],
    Phase.BIDDING: [],
    Phase.MAIN_DUE_DILIGENCE: [],
    Phase.NEGOTIATION: [],
    Phase.CLOSING: [],
    Phase.POST_CLOSING: [],
}

# 유효한 상태 전환
_VALID_STATUS_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.DRAFT: {TransactionStatus.ACTIVE, TransactionStatus.TERMINATED},
    TransactionStatus.ACTIVE: {TransactionStatus.ON_HOLD, TransactionStatus.COMPLETED, TransactionStatus.TERMINATED},
    TransactionStatus.ON_HOLD: {TransactionStatus.ACTIVE, TransactionStatus.TERMINATED},
    TransactionStatus.COMPLETED: set(),
    TransactionStatus.TERMINATED: set(),
}


async def get_phase_completion(db: AsyncSession, txn: Transaction) -> PhaseCompletionStatus:
    """현재 단계의 완료 상태를 평가한다."""
    idx = _PHASE_INDEX.get(txn.phase)
    if idx is None:
        raise WorkflowError(f"지원되지 않는 단계입니다: {txn.phase}")
    next_phase = _PHASE_ORDER[idx + 1] if idx < len(_PHASE_ORDER) - 1 else None
    prev_phase = _PHASE_ORDER[idx - 1] if idx > 0 else None

    prerequisites: list[PhasePrerequisite] = []

    # 1) Transaction 필드 기반 전제 조건 (기존 로직)
    if next_phase and next_phase in _PHASE_PREREQUISITES:
        for field, label in _PHASE_PREREQUISITES[next_phase]:
            val = getattr(txn, field, None)
            satisfied = val is not None and val != ""
            prerequisites.append(PhasePrerequisite(field=field, label=label, satisfied=satisfied))

    # 2) DB 쿼리 기반 gate validator (신규)
    if next_phase and next_phase in PHASE_GATE_VALIDATORS:
        for validator in PHASE_GATE_VALIDATORS[next_phase]:
            prereqs = await validator(db, txn)
            prerequisites.extend(prereqs)

    all_met = all(p.satisfied for p in prerequisites) if prerequisites else True
    can_advance = all_met and next_phase is not None and txn.status == TransactionStatus.ACTIVE

    blocking_reasons: list[str] = []
    if not can_advance:
        if not all_met:
            unmet = [p.label for p in prerequisites if not p.satisfied]
            blocking_reasons.extend(unmet)
        elif next_phase is None:
            blocking_reasons.append("마지막 단계입니다")
        elif txn.status != TransactionStatus.ACTIVE:
            blocking_reasons.append(f"거래 상태가 {txn.status.value}입니다 (ACTIVE 필요)")

    gate_summary = PHASE_GATE_SUMMARIES.get(next_phase) if next_phase else None

    pending_acks = [p.field for p in prerequisites if p.requires_acknowledgement and p.satisfied]

    return PhaseCompletionStatus(
        current_phase=txn.phase,
        prerequisites=prerequisites,
        all_met=all_met,
        can_advance=can_advance,
        blocking_reasons=blocking_reasons,
        next_phase=next_phase,
        previous_phase=prev_phase,
        gate_summary=gate_summary,
        pending_acknowledgements=pending_acks,
        requires_user_acknowledgement=len(pending_acks) > 0,
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
    """단계를 전환한다. 1단계만 앞/뒤로 이동 가능."""
    if txn.status != TransactionStatus.ACTIVE:
        raise WorkflowError("ACTIVE 상태의 거래만 단계를 전환할 수 있습니다")

    from_idx = _PHASE_INDEX.get(txn.phase)
    if from_idx is None:
        raise WorkflowError(f"지원되지 않는 단계입니다: {txn.phase}")
    to_idx = _PHASE_INDEX.get(to_phase)
    if to_idx is None:
        raise WorkflowError(f"잘못된 단계: {to_phase}")

    diff = to_idx - from_idx
    if diff not in (1, -1):
        raise WorkflowError(
            f"{txn.phase.value} → {to_phase.value} 전환은 허용되지 않습니다. 한 단계 앞/뒤로만 이동할 수 있습니다."
        )

    # 전진 시 전제 조건 체크 (gate validator 포함)
    if diff == 1:
        completion = await get_phase_completion(db, txn)
        if not completion.all_met:
            unmet = [p.label for p in completion.prerequisites if not p.satisfied]
            raise WorkflowError(f"다음 단계로 진행하려면 필수 조건을 충족해야 합니다: {', '.join(unmet)}")

        # Acknowledgement 검증: requires_acknowledgement=True인 항목은 명시적 확인 필요
        ack = acknowledgements or {}
        unacked = [
            p.label for p in completion.prerequisites if p.requires_acknowledgement and not ack.get(p.field, False)
        ]
        if unacked:
            raise WorkflowError(f"다음 항목에 대한 확인이 필요합니다: {', '.join(unacked)}")

    from_phase = txn.phase
    txn.phase = to_phase

    # 타임라인 자동 이벤트
    event = DealTimeline(
        transaction_id=txn.id,
        event_type="PHASE_TRANSITION",
        title=f"{from_phase.value} → {to_phase.value}",
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
    """단계 전환을 위한 승인 요청을 생성한다."""
    if txn.status != TransactionStatus.ACTIVE:
        raise WorkflowError("ACTIVE 상태의 거래만 승인을 요청할 수 있습니다")

    from_idx = _PHASE_INDEX.get(txn.phase)
    if from_idx is None:
        raise WorkflowError(f"지원되지 않는 단계입니다: {txn.phase}")
    to_idx = _PHASE_INDEX.get(to_phase)
    if to_idx is None or (to_idx - from_idx) != 1:
        raise WorkflowError(f"{txn.phase.value} → {to_phase.value} 단계 전환에 대한 승인 요청은 허용되지 않습니다")

    # 전제 조건 체크
    completion = await get_phase_completion(db, txn)
    if not completion.all_met:
        unmet = [p.label for p in completion.prerequisites if not p.satisfied]
        raise WorkflowError(f"승인 요청 전 필수 조건을 충족해야 합니다: {', '.join(unmet)}")

    approvers = [
        {"email": e, "role": "APPROVER", "status": "PENDING", "comment": None, "decided_at": None}
        for e in approver_emails
    ]

    approval = ApprovalRequest(
        transaction_id=txn.id,
        requester_email=actor_email or "",
        approval_type=ApprovalType.PHASE_ADVANCE,
        title=f"단계 전환 승인: {txn.phase.value} → {to_phase.value}",
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
    """거래 상태를 변경한다."""
    valid = _VALID_STATUS_TRANSITIONS.get(txn.status, set())
    if to_status not in valid:
        raise WorkflowError(f"{txn.status.value} → {to_status.value} 상태 전환은 허용되지 않습니다")

    from_status = txn.status
    txn.status = to_status

    # 타임라인 자동 이벤트
    event = DealTimeline(
        transaction_id=txn.id,
        event_type="STATUS_CHANGE",
        title=f"상태 변경: {from_status.value} → {to_status.value}",
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
