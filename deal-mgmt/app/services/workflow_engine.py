"""8단계 M&A 워크플로우 상태 머신.

Phase 순서: ENGAGEMENT → PREPARATION → MARKETING → BIDDING → MAIN_DUE_DILIGENCE → NEGOTIATION → CLOSING → POST_CLOSING
전환 규칙: 한 단계 앞/뒤로만 이동 가능, 건너뛰기 불가.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowError
from app.core.log_decorators import log_error_with_input
from app.models.approval import ApprovalRequest
from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.closing_checklist import ClosingChecklist
from app.models.compliance_item import ComplianceItem
from app.models.contract import Contract
from app.models.dd_checklist import DDChecklist
from app.models.enums import (
    ApprovalType,
    AuditAction,
    BidStatus,
    BuyerCandidateStatus,
    ClosingConditionStatus,
    ComplianceStatus,
    ContractType,
    DDChecklistStatus,
    RiskSeverity,
    RiskStatus,
    TransactionPhase,
    TransactionStatus,
)
from app.models.enums import (
    TransactionPhase as Phase,
)
from app.models.marketing_material import MarketingMaterial
from app.models.risk_item import RiskItem
from app.models.timeline import DealTimeline
from app.models.transaction import Transaction
from app.schemas.workflow import PhaseCompletionStatus, PhasePrerequisite
from app.services import audit_service

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

# 단계별 게이트 요약 메시지
_PHASE_GATE_SUMMARIES: dict[TransactionPhase, str] = {
    Phase.BIDDING: "입찰 진입: Short List 매수자 및 NDA/자료 배포 완료 필요",
    Phase.MAIN_DUE_DILIGENCE: "본실사 진입: 유효 입찰(IOI/LOI) 1건 이상 필요",
    Phase.NEGOTIATION: "협상 진입: DD 완료 및 Critical 리스크 해소 필요",
    Phase.CLOSING: "Closing 진입: 계약 체결, 체크리스트 완료, 리스크/컴플라이언스 해소 필요",
}

# ── Gate Validator 타입 ────────────────────────────────────
GateValidator = Callable[
    [AsyncSession, Transaction],
    Coroutine[Any, Any, list[PhasePrerequisite]],
]


# ── 개별 Gate Validator 함수들 ──────────────────────────────


async def _validate_has_short_list(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """Short List 매수자 1명 이상 존재 여부 확인."""
    count_q = sa_select(sa_func.count(BuyerCandidate.id)).where(
        BuyerCandidate.transaction_id == txn.id,
        BuyerCandidate.is_short_listed.is_(True),
    )
    count = (await db.execute(count_q)).scalar() or 0
    return [
        PhasePrerequisite(
            field="short_list_buyers",
            label="Short List 매수자",
            satisfied=count >= 1,
            current_value=f"{count}명",
            target_value="1명 이상",
        )
    ]


async def _validate_has_nda_or_distribution(
    db: AsyncSession,
    txn: Transaction,
) -> list[PhasePrerequisite]:
    """NDA 체결 매수자 또는 배포 완료 자료 존재 여부 확인."""
    nda_statuses = [
        BuyerCandidateStatus.NDA_SIGNED,
        BuyerCandidateStatus.CIM_SENT,
        BuyerCandidateStatus.INTEREST_CONFIRMED,
        BuyerCandidateStatus.IOI_RECEIVED,
        BuyerCandidateStatus.IOI_ACCEPTED,
        BuyerCandidateStatus.DD_GRANTED,
        BuyerCandidateStatus.DD_IN_PROGRESS,
        BuyerCandidateStatus.LOI_RECEIVED,
        BuyerCandidateStatus.LOI_ACCEPTED,
        BuyerCandidateStatus.SELECTED,
        BuyerCandidateStatus.BID_SUBMITTED,
    ]
    nda_q = sa_select(sa_func.count(BuyerCandidate.id)).where(
        BuyerCandidate.transaction_id == txn.id,
        BuyerCandidate.status.in_(nda_statuses),
    )
    nda_count = (await db.execute(nda_q)).scalar() or 0

    dist_q = sa_select(sa_func.count(MarketingMaterial.id)).where(
        MarketingMaterial.transaction_id == txn.id,
        MarketingMaterial.distributed_to.isnot(None),
    )
    dist_count = (await db.execute(dist_q)).scalar() or 0

    satisfied = nda_count >= 1 or dist_count >= 1
    return [
        PhasePrerequisite(
            field="nda_or_distribution",
            label="NDA 체결 또는 자료 배포",
            satisfied=satisfied,
            current_value=f"NDA {nda_count}건, 배포 {dist_count}건",
            target_value="1건 이상",
        )
    ]


async def _validate_has_valid_bid(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """유효 입찰(IOI/LOI) 1건 이상 존재 여부 확인."""
    valid_statuses = [BidStatus.SUBMITTED, BidStatus.UNDER_REVIEW, BidStatus.ACCEPTED]
    bid_q = sa_select(sa_func.count(Bid.id)).where(
        Bid.transaction_id == txn.id,
        Bid.status.in_(valid_statuses),
    )
    count = (await db.execute(bid_q)).scalar() or 0
    return [
        PhasePrerequisite(
            field="valid_bids",
            label="유효 입찰 (IOI/LOI)",
            satisfied=count >= 1,
            current_value=f"{count}건",
            target_value="1건 이상",
        )
    ]


async def _validate_dd_threshold(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """DD 완료율 확인. 항목 0개면 non-blocking (satisfied=True)."""
    total_q = sa_select(sa_func.count(DDChecklist.id)).where(
        DDChecklist.transaction_id == txn.id,
    )
    total = (await db.execute(total_q)).scalar() or 0

    if total == 0:
        return [
            PhasePrerequisite(
                field="dd_completion",
                label="DD 체크리스트 완료",
                satisfied=True,
                current_value="항목 없음 (해당 없음)",
            )
        ]

    done_q = sa_select(sa_func.count(DDChecklist.id)).where(
        DDChecklist.transaction_id == txn.id,
        DDChecklist.status.in_([DDChecklistStatus.COMPLETED, DDChecklistStatus.NOT_APPLICABLE]),
    )
    done = (await db.execute(done_q)).scalar() or 0
    pct = round(done / total * 100)
    return [
        PhasePrerequisite(
            field="dd_completion",
            label="DD 체크리스트 완료",
            satisfied=pct >= 80,
            current_value=f"{done}/{total} ({pct}%)",
            target_value="80% 이상",
        )
    ]


async def _validate_no_critical_risks(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """미완화 Critical 리스크 0건 확인."""
    risk_q = sa_select(sa_func.count(RiskItem.id)).where(
        RiskItem.transaction_id == txn.id,
        RiskItem.severity == RiskSeverity.CRITICAL,
        RiskItem.status.notin_([RiskStatus.MITIGATED, RiskStatus.CLOSED, RiskStatus.ACCEPTED]),
    )
    count = (await db.execute(risk_q)).scalar() or 0
    return [
        PhasePrerequisite(
            field="critical_risks",
            label="미완화 Critical 리스크",
            satisfied=count == 0,
            current_value=f"{count}건",
            target_value="0건",
        )
    ]


async def _validate_no_non_compliant(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """Non-compliant 항목 0건 확인."""
    nc_q = sa_select(sa_func.count(ComplianceItem.id)).where(
        ComplianceItem.transaction_id == txn.id,
        ComplianceItem.status == ComplianceStatus.NON_COMPLIANT,
    )
    count = (await db.execute(nc_q)).scalar() or 0
    return [
        PhasePrerequisite(
            field="non_compliant",
            label="미준수 컴플라이언스",
            satisfied=count == 0,
            current_value=f"{count}건",
            target_value="0건",
        )
    ]


async def _validate_has_contract(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """SPA/BTA 계약 초안 1건 이상 존재 확인."""
    contract_q = sa_select(sa_func.count(Contract.id)).where(
        Contract.transaction_id == txn.id,
        Contract.contract_type.in_([ContractType.SPA, ContractType.BTA]),
    )
    count = (await db.execute(contract_q)).scalar() or 0
    return [
        PhasePrerequisite(
            field="contracts",
            label="SPA/BTA 계약",
            satisfied=count >= 1,
            current_value=f"{count}건",
            target_value="1건 이상",
        )
    ]


async def _validate_closing_checklist(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
    """Closing 체크리스트 전체 완료 확인. 항목 0개면 non-blocking."""
    total_q = sa_select(sa_func.count(ClosingChecklist.id)).where(
        ClosingChecklist.transaction_id == txn.id,
    )
    total = (await db.execute(total_q)).scalar() or 0

    if total == 0:
        return [
            PhasePrerequisite(
                field="closing_checklist",
                label="Closing 체크리스트",
                satisfied=True,
                current_value="항목 없음 (해당 없음)",
            )
        ]

    done_statuses = [
        ClosingConditionStatus.COMPLETED,
        ClosingConditionStatus.WAIVED,
        ClosingConditionStatus.NOT_APPLICABLE,
    ]
    done_q = sa_select(sa_func.count(ClosingChecklist.id)).where(
        ClosingChecklist.transaction_id == txn.id,
        ClosingChecklist.status.in_(done_statuses),
    )
    done = (await db.execute(done_q)).scalar() or 0
    remaining = total - done
    return [
        PhasePrerequisite(
            field="closing_checklist",
            label="Closing 체크리스트",
            satisfied=remaining == 0,
            current_value=f"{done}/{total} 완료 (잔여 {remaining}건)",
            target_value="전체 완료",
        )
    ]


# ── Gate Validator Registry ────────────────────────────────
_PHASE_GATE_VALIDATORS: dict[TransactionPhase, list[GateValidator]] = {
    Phase.BIDDING: [_validate_has_short_list, _validate_has_nda_or_distribution],
    Phase.MAIN_DUE_DILIGENCE: [_validate_has_valid_bid],
    Phase.NEGOTIATION: [_validate_dd_threshold, _validate_no_critical_risks],
    Phase.CLOSING: [
        _validate_has_contract,
        _validate_closing_checklist,
        _validate_no_critical_risks,
        _validate_no_non_compliant,
    ],
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
    if next_phase and next_phase in _PHASE_GATE_VALIDATORS:
        for validator in _PHASE_GATE_VALIDATORS[next_phase]:
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

    gate_summary = _PHASE_GATE_SUMMARIES.get(next_phase) if next_phase else None

    return PhaseCompletionStatus(
        current_phase=txn.phase,
        prerequisites=prerequisites,
        all_met=all_met,
        can_advance=can_advance,
        blocking_reasons=blocking_reasons,
        next_phase=next_phase,
        previous_phase=prev_phase,
        gate_summary=gate_summary,
    )


@log_error_with_input
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
        new_value={"phase": to_phase},
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
