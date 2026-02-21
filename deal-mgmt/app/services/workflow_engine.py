"""7단계 M&A 워크플로우 상태 머신.

Phase 순서: ENGAGEMENT → PREPARATION → MARKETING → BIDDING_DD → NEGOTIATION → CLOSING → POST_CLOSING
전환 규칙: 한 단계 앞/뒤로만 이동 가능, 건너뛰기 불가.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowError
from app.models.approval import ApprovalRequest
from app.models.compliance_item import ComplianceItem
from app.models.enums import (
    ApprovalStatus,
    ApprovalType,
    AuditAction,
    ComplianceStatus,
    RiskSeverity,
    RiskStatus,
    TransactionPhase,
    TransactionStatus,
)
from app.models.enums import (
    TransactionPhase as Phase,
)
from app.models.risk_item import RiskItem
from app.models.timeline import DealTimeline
from app.models.transaction import Transaction
from app.schemas.workflow import PhaseCompletionStatus, PhasePrerequisite
from app.services import audit_service

# 순서가 있는 7단계
_PHASE_ORDER: list[TransactionPhase] = [
    Phase.ENGAGEMENT,
    Phase.PREPARATION,
    Phase.MARKETING,
    Phase.BIDDING_DD,
    Phase.NEGOTIATION,
    Phase.CLOSING,
    Phase.POST_CLOSING,
]

_PHASE_INDEX: dict[TransactionPhase, int] = {p: i for i, p in enumerate(_PHASE_ORDER)}

# 단계별 최소 전제 조건 (필드 기반)
_PHASE_PREREQUISITES: dict[TransactionPhase, list[tuple[str, str]]] = {
    Phase.ENGAGEMENT: [],
    Phase.PREPARATION: [
        ("client_name", "클라이언트 정보"),
        ("lead_advisor_email", "리드 어드바이저"),
    ],
    Phase.MARKETING: [
        ("target_company_name", "대상 기업 정보"),
        ("industry", "산업 분류"),
    ],
    Phase.BIDDING_DD: [
        ("deal_structure", "딜 구조"),
    ],
    Phase.NEGOTIATION: [
        ("estimated_deal_value", "예상 거래 금액"),
    ],
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


def get_phase_completion(txn: Transaction) -> PhaseCompletionStatus:
    """현재 단계의 완료 상태를 평가한다."""
    idx = _PHASE_INDEX[txn.phase]
    next_phase = _PHASE_ORDER[idx + 1] if idx < len(_PHASE_ORDER) - 1 else None
    prev_phase = _PHASE_ORDER[idx - 1] if idx > 0 else None

    prerequisites: list[PhasePrerequisite] = []
    if next_phase and next_phase in _PHASE_PREREQUISITES:
        for field, label in _PHASE_PREREQUISITES[next_phase]:
            val = getattr(txn, field, None)
            satisfied = val is not None and val != ""
            prerequisites.append(PhasePrerequisite(field=field, label=label, satisfied=satisfied))

    all_met = all(p.satisfied for p in prerequisites) if prerequisites else True
    can_advance = all_met and next_phase is not None and txn.status == TransactionStatus.ACTIVE

    return PhaseCompletionStatus(
        current_phase=txn.phase,
        prerequisites=prerequisites,
        all_met=all_met,
        can_advance=can_advance,
        next_phase=next_phase,
        previous_phase=prev_phase,
    )


async def advance_phase(
    db: AsyncSession,
    txn: Transaction,
    to_phase: TransactionPhase,
    actor_email: str | None = None,
    notes: str | None = None,
) -> Transaction:
    """단계를 전환한다. 1단계만 앞/뒤로 이동 가능."""
    if txn.status != TransactionStatus.ACTIVE:
        raise WorkflowError("ACTIVE 상태의 거래만 단계를 전환할 수 있습니다")

    from_idx = _PHASE_INDEX[txn.phase]
    to_idx = _PHASE_INDEX.get(to_phase)
    if to_idx is None:
        raise WorkflowError(f"잘못된 단계: {to_phase}")

    diff = to_idx - from_idx
    if diff not in (1, -1):
        raise WorkflowError(
            f"{txn.phase.value} → {to_phase.value} 전환은 허용되지 않습니다. 한 단계 앞/뒤로만 이동할 수 있습니다."
        )

    # 전진 시 전제 조건 체크
    if diff == 1:
        completion = get_phase_completion(txn)
        if not completion.all_met:
            unmet = [p.label for p in completion.prerequisites if not p.satisfied]
            raise WorkflowError(f"다음 단계로 진행하려면 필수 조건을 충족해야 합니다: {', '.join(unmet)}")

    # NEGOTIATION → CLOSING: 리스크/컴플라이언스 게이트
    if diff == 1 and to_phase == Phase.CLOSING:
        await _check_risk_compliance_gate(db, txn)

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
        old_value={"phase": from_phase.value},
        new_value={"phase": to_phase.value},
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

    from_idx = _PHASE_INDEX[txn.phase]
    to_idx = _PHASE_INDEX.get(to_phase)
    if to_idx is None or (to_idx - from_idx) != 1:
        raise WorkflowError(f"{txn.phase.value} → {to_phase.value} 단계 전환에 대한 승인 요청은 허용되지 않습니다")

    # 전제 조건 체크
    completion = get_phase_completion(txn)
    if not completion.all_met:
        unmet = [p.label for p in completion.prerequisites if not p.satisfied]
        raise WorkflowError(f"승인 요청 전 필수 조건을 충족해야 합니다: {', '.join(unmet)}")

    approvers = [{"email": e, "role": "APPROVER", "status": "PENDING", "comment": None, "decided_at": None} for e in approver_emails]

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
        new_value={"from_phase": txn.phase.value, "to_phase": to_phase.value},
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
        old_value={"status": from_status.value},
        new_value={"status": to_status.value},
        notes=reason,
    )
    await db.commit()
    await db.refresh(txn)
    return txn


async def _check_risk_compliance_gate(db: AsyncSession, txn: Transaction) -> None:
    """CLOSING 진입 시 미완화 Critical 리스크 및 non-compliant 항목 차단."""
    # 미완화 Critical 리스크
    q = sa_select(RiskItem).where(
        RiskItem.transaction_id == txn.id,
        RiskItem.severity == RiskSeverity.CRITICAL,
        RiskItem.status.notin_([RiskStatus.MITIGATED, RiskStatus.CLOSED, RiskStatus.ACCEPTED]),
    )
    result = await db.execute(q)
    critical_risks = list(result.scalars().all())
    if critical_risks:
        titles = [r.title for r in critical_risks[:3]]
        raise WorkflowError(
            f"클로징 진입 전 미완화 Critical 리스크를 해결해야 합니다: {', '.join(titles)}"
            + (f" 외 {len(critical_risks) - 3}건" if len(critical_risks) > 3 else "")
        )

    # Non-compliant 항목
    q2 = sa_select(ComplianceItem).where(
        ComplianceItem.transaction_id == txn.id,
        ComplianceItem.status == ComplianceStatus.NON_COMPLIANT,
    )
    result2 = await db.execute(q2)
    nc_items = list(result2.scalars().all())
    if nc_items:
        reqs = [c.requirement for c in nc_items[:3]]
        raise WorkflowError(
            f"클로징 진입 전 미준수 컴플라이언스 항목을 해결해야 합니다: {', '.join(reqs)}"
            + (f" 외 {len(nc_items) - 3}건" if len(nc_items) > 3 else "")
        )
