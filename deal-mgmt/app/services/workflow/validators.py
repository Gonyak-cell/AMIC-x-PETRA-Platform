"""Phase Gate Validator — 각 단계 전환의 전제 조건을 DB 쿼리로 평가한다."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.closing_checklist import ClosingChecklist
from app.models.compliance_item import ComplianceItem
from app.models.contract import Contract
from app.models.dd_checklist import DDChecklist
from app.models.enums import (
    BidStatus,
    BuyerCandidateStatus,
    ClosingConditionStatus,
    ComplianceStatus,
    ContractType,
    DDChecklistStatus,
    RiskSeverity,
    RiskStatus,
    TransactionPhase,
)
from app.models.enums import TransactionPhase as Phase
from app.models.marketing_material import MarketingMaterial
from app.models.risk_item import RiskItem
from app.models.transaction import Transaction
from app.schemas.workflow import PhasePrerequisite

# ── Gate Validator 타입 ────────────────────────────────────
GateValidator = Callable[
    [AsyncSession, Transaction],
    Coroutine[Any, Any, list[PhasePrerequisite]],
]


# ── 개별 Gate Validator 함수들 ──────────────────────────────


async def validate_has_short_list(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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


async def validate_has_nda_or_distribution(
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


async def validate_has_valid_bid(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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


async def validate_dd_threshold(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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
                current_value="항목 없음 — 확인 필요",
                requires_acknowledgement=True,
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


async def validate_no_critical_risks(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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


async def validate_no_non_compliant(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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


async def validate_has_contract(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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


async def validate_closing_checklist(db: AsyncSession, txn: Transaction) -> list[PhasePrerequisite]:
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
                current_value="항목 없음 — 확인 필요",
                requires_acknowledgement=True,
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
PHASE_GATE_VALIDATORS: dict[TransactionPhase, list[GateValidator]] = {
    Phase.BIDDING: [validate_has_short_list, validate_has_nda_or_distribution],
    Phase.MAIN_DUE_DILIGENCE: [validate_has_valid_bid],
    Phase.NEGOTIATION: [validate_dd_threshold, validate_no_critical_risks],
    Phase.CLOSING: [
        validate_has_contract,
        validate_closing_checklist,
        validate_no_critical_risks,
        validate_no_non_compliant,
    ],
}

# 단계별 게이트 요약 메시지
PHASE_GATE_SUMMARIES: dict[TransactionPhase, str] = {
    Phase.BIDDING: "입찰 진입: Short List 매수자 및 NDA/자료 배포 완료 필요",
    Phase.MAIN_DUE_DILIGENCE: "본실사 진입: 유효 입찰(IOI/LOI) 1건 이상 필요",
    Phase.NEGOTIATION: "협상 진입: DD 완료 및 Critical 리스크 해소 필요",
    Phase.CLOSING: "Closing 진입: 계약 체결, 체크리스트 완료, 리스크/컴플라이언스 해소 필요",
}
