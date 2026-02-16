"""QoE 계산 서비스 — FDD-501/502/503 오케스트레이션.

DB에서 데이터 조회 → 엔진 호출 → 결과 저장.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ErrorCode
from app.core.exceptions import CalculationError, NotFoundError
from app.core.logging import get_logger
from app.industry import get_fdd_industry_module_safe
from app.models.deal import Deal
from app.engines.qoe_engine import (
    ENGINE_VERSION,
    CategoryTotal,
    build_qoe_bridge,
    calculate_reported_ebitda,
    detect_adjustment_candidates,
)
from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.audit import AuditAction, AuditLog
from app.models.evidence import EvidenceLink, SourceType
from app.models.journal_entry import JournalEntry
from app.models.qoe import (
    AdjustmentCategory,
    AdjustmentItem,
    AdjustmentStatus,
    QoECalculation,
    QoEStatus,
)
from app.models.standard_line_item import (
    FinancialStatement,
    LineItemCategory,
    StandardLineItem,
)
from app.schemas.qoe import (
    AdjustmentItemApprove,
    AdjustmentItemCreate,
    AdjustmentItemUpdate,
)

logger = get_logger(__name__)


# ── Internal Helpers ─────────────────────────────────────


def _get_tb_accounts(
    db: Session,
    deal_id: uuid.UUID,
    entity_id: uuid.UUID | None = None,
) -> dict[str, Decimal]:
    """TB 계정별 잔액 맵. {account_code: balance}."""
    stmt = select(JournalEntry).where(
        JournalEntry.deal_id == deal_id,
        JournalEntry.source_type == "TB",
    )
    if entity_id is not None:
        stmt = stmt.where(JournalEntry.entity_id == entity_id)
    entries = list(db.scalars(stmt))
    tb_map: dict[str, Decimal] = {}
    for e in entries:
        if e.account_code:
            balance = e.balance or Decimal("0")
            tb_map[e.account_code] = tb_map.get(e.account_code, Decimal("0")) + balance
    return tb_map


def _get_line_items_map(
    db: Session,
    codes: set[str] | None = None,
) -> dict[str, StandardLineItem]:
    """표준 라인아이템 코드 → 객체 맵.

    codes가 주어지면 해당 코드만 로드하여 성능을 개선한다.
    """
    stmt = select(StandardLineItem)
    if codes:
        stmt = stmt.where(StandardLineItem.code.in_(codes))
    items = list(db.scalars(stmt))
    return {item.code: item for item in items}


def _aggregate_tb_by_category(
    db: Session,
    deal_id: uuid.UUID,
) -> list[CategoryTotal]:
    """APPROVED 매핑 기준으로 TB 잔액을 IS 카테고리별로 집계한다."""
    mappings = list(
        db.scalars(
            select(AccountMapping).where(
                AccountMapping.deal_id == deal_id,
                AccountMapping.status == MappingStatus.APPROVED,
            )
        )
    )
    # FX-aware: 외화 항목이 있으면 환율 변환 적용
    deal = db.get(Deal, deal_id)
    if deal:
        from app.services.fx.fx_aware_tb import get_tb_accounts_fx_aware

        tb_map = get_tb_accounts_fx_aware(db, deal_id, deal)
    else:
        tb_map = _get_tb_accounts(db, deal_id)
    target_codes = {m.target_line_item_code for m in mappings}
    li_map = _get_line_items_map(db, codes=target_codes)

    cat_accounts: dict[str, list[dict]] = {}
    for mapping in mappings:
        li = li_map.get(mapping.target_line_item_code)
        if not li:
            continue
        # IS only, skip subtotals
        if li.statement_type != FinancialStatement.IS:
            continue
        if li.is_subtotal:
            continue

        cat_key = li.category.value
        balance = tb_map.get(mapping.source_account_code, Decimal("0"))

        if cat_key not in cat_accounts:
            cat_accounts[cat_key] = []
        cat_accounts[cat_key].append(
            {
                "code": mapping.source_account_code,
                "name": mapping.source_account_name,
                "amount": str(balance),
            }
        )

    result: list[CategoryTotal] = []
    for cat_key, accounts in cat_accounts.items():
        total = sum(Decimal(a["amount"]) for a in accounts)
        result.append(
            CategoryTotal(
                category=cat_key,
                total=total,
                account_count=len(accounts),
                accounts=accounts,
            )
        )
    return result


def _get_gl_entries(db: Session, deal_id: uuid.UUID) -> list[dict]:
    """GL 전표를 dict 리스트로 변환."""
    entries = list(
        db.scalars(
            select(JournalEntry).where(
                JournalEntry.deal_id == deal_id,
                JournalEntry.source_type == "GL",
            )
        )
    )
    return [
        {
            "entry_id": e.entry_id or "",
            "account_code": e.account_code or "",
            "account_name": e.account_name or "",
            "amount": str(e.amount or e.debit or Decimal("0")),
            "description": e.description or "",
            "entry_date": str(e.entry_date) if e.entry_date else "",
        }
        for e in entries
    ]


def _get_non_operating_codes(
    db: Session,
    deal_id: uuid.UUID,
) -> set[str]:
    """NON_OPERATING 카테고리로 매핑된 계정코드 set."""
    mappings = list(
        db.scalars(
            select(AccountMapping).where(
                AccountMapping.deal_id == deal_id,
                AccountMapping.status == MappingStatus.APPROVED,
            )
        )
    )
    li_map = _get_line_items_map(db)
    non_op_cats = {
        LineItemCategory.NON_OPERATING.value,
        LineItemCategory.INTEREST_INCOME.value,
        LineItemCategory.INTEREST_EXPENSE.value,
    }

    result: set[str] = set()
    for m in mappings:
        li = li_map.get(m.target_line_item_code)
        if li and li.category.value in non_op_cats:
            result.add(m.source_account_code)
    return result


# ── Main QoE Calculation ─────────────────────────────────


def run_qoe_calculation(
    db: Session,
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID,
) -> QoECalculation:
    """QoE 계산을 실행하고 결과를 저장한다.

    1. APPROVED 매핑 기준으로 TB 잔액을 카테고리별로 집계
    2. Reported EBITDA 계산 (순수 엔진)
    3. GL에서 조정 후보 탐지 (순수 엔진)
    4. 초기 Bridge 구축 (adjustments=0)
    5. DB에 결과 저장 + AuditLog + EvidenceLinks
    """
    # 1. Aggregate TB by IS category
    category_totals = _aggregate_tb_by_category(db, deal_id)
    if not category_totals:
        raise CalculationError(
            ErrorCode.QOE_PERIOD_MISMATCH,
            "No approved IS mappings found. Complete account mapping first.",
        )

    # 2. Calculate Reported EBITDA (pure engine)
    ebitda_result, evidence_data = calculate_reported_ebitda(category_totals)

    # 3. Detect adjustment candidates from GL (with industry context)
    gl_entries = _get_gl_entries(db, deal_id)
    non_op_codes = _get_non_operating_codes(db, deal_id)

    deal = db.get(Deal, deal_id)
    industry_ctx = None
    if deal and deal.industry:
        industry_module = get_fdd_industry_module_safe(deal.industry.value)
        industry_ctx = industry_module.get_context()

    candidates = detect_adjustment_candidates(
        gl_entries, non_op_codes, ebitda_result.revenue,
        industry_context=industry_ctx,
    )

    # 4. Build initial bridge (no approved adjustments yet)
    bridge = build_qoe_bridge(ebitda_result.reported_ebitda, [])

    # 5. Persist QoECalculation
    qoe = QoECalculation(
        deal_id=deal_id,
        snapshot_id=snapshot_id,
        revenue=ebitda_result.revenue,
        cogs=ebitda_result.cogs,
        gross_profit=ebitda_result.gross_profit,
        sga=ebitda_result.sga,
        depreciation_amortization=ebitda_result.depreciation_amortization,
        other_operating=ebitda_result.other_operating,
        operating_income=ebitda_result.operating_income,
        reported_ebitda=ebitda_result.reported_ebitda,
        total_adjustments=bridge.total_adjustments,
        adjusted_ebitda=bridge.adjusted_ebitda,
        balance_check_error=bridge.balance_check_error,
        category_breakdown=ebitda_result.category_breakdown,
        engine_version=ENGINE_VERSION,
        status=QoEStatus.DRAFT,
    )
    db.add(qoe)
    db.flush()  # .id 참조를 위해 flush

    # 6. Persist adjustment candidates
    for i, cand in enumerate(candidates):
        adj = AdjustmentItem(
            qoe_calculation_id=qoe.id,
            deal_id=deal_id,
            category=AdjustmentCategory(cand.category),
            description=cand.description,
            amount=cand.amount,
            detection_method=cand.detection_method,
            confidence_score=cand.confidence_score,
            source_account_code=cand.source_account_code,
            source_account_name=cand.source_account_name,
            source_entry_ids=cand.source_entry_ids,
            status=AdjustmentStatus.CANDIDATE,
            display_order=i,
        )
        db.add(adj)

    # 7. AuditLog
    db.flush()
    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="qoe_calculation",
            entity_id=qoe.id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "reported_ebitda": str(ebitda_result.reported_ebitda),
                "adjusted_ebitda": str(bridge.adjusted_ebitda),
                "adjustment_candidates": len(candidates),
                "engine_version": ENGINE_VERSION,
            },
        )
    )

    # 8. Create EvidenceLinks for TB sources
    for ev in evidence_data:
        if not ev.source_id:
            continue
        link = EvidenceLink(
            deal_id=deal_id,
            target_type=ev.target_type,
            target_id=qoe.id,
            source_type=SourceType.TB,
            source_id=ev.source_id,
            source_detail=ev.source_detail,
            engine_version=ENGINE_VERSION,
            snapshot_id=snapshot_id,
        )
        db.add(link)

    db.commit()
    db.refresh(qoe)
    return qoe


# ── Bridge Recalculation ─────────────────────────────────


def recalculate_bridge(
    db: Session,
    qoe_id: uuid.UUID,
) -> QoECalculation:
    """APPROVED 조정항목 기준으로 Bridge를 재계산한다."""
    qoe = db.get(QoECalculation, qoe_id)
    if not qoe:
        raise NotFoundError("QoECalculation", str(qoe_id))

    # APPROVED adjustments만 합산
    approved_adjs = [
        a for a in qoe.adjustments if a.status == AdjustmentStatus.APPROVED
    ]
    from app.engines.qoe_engine import AdjustmentCandidateData

    bridge_items = [
        AdjustmentCandidateData(
            category=a.category.value,
            description=a.description,
            amount=a.amount,
            detection_method=a.detection_method,
            confidence_score=a.confidence_score or Decimal("0"),
            source_account_code=a.source_account_code,
            source_account_name=a.source_account_name,
        )
        for a in approved_adjs
    ]
    bridge = build_qoe_bridge(qoe.reported_ebitda, bridge_items)

    # Validate balance
    if bridge.balance_check_error != Decimal("0.0000"):
        raise CalculationError(
            ErrorCode.QOE_BRIDGE_IMBALANCE,
            f"Bridge balance error: {bridge.balance_check_error}",
        )

    old_adjusted = str(qoe.adjusted_ebitda)
    qoe.total_adjustments = bridge.total_adjustments
    qoe.adjusted_ebitda = bridge.adjusted_ebitda
    qoe.balance_check_error = bridge.balance_check_error

    db.flush()
    db.add(
        AuditLog(
            deal_id=qoe.deal_id,
            entity_type="qoe_calculation",
            entity_id=qoe.id,
            action=AuditAction.UPDATE,
            actor="system",
            old_value={"adjusted_ebitda": old_adjusted},
            new_value={
                "adjusted_ebitda": str(bridge.adjusted_ebitda),
                "total_adjustments": str(bridge.total_adjustments),
                "approved_count": len(approved_adjs),
            },
        )
    )
    db.commit()
    db.refresh(qoe)
    return qoe


# ── Adjustment CRUD ──────────────────────────────────────


def add_manual_adjustment(
    db: Session,
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    data: AdjustmentItemCreate,
) -> AdjustmentItem:
    """수동 조정항목을 추가한다."""
    qoe = db.get(QoECalculation, qoe_id)
    if not qoe or qoe.deal_id != deal_id:
        raise NotFoundError("QoECalculation", str(qoe_id))

    max_order = max((a.display_order for a in qoe.adjustments), default=-1)
    adj = AdjustmentItem(
        qoe_calculation_id=qoe_id,
        deal_id=deal_id,
        category=data.category,
        description=data.description,
        amount=data.amount,
        detection_method="manual",
        status=AdjustmentStatus.PROPOSED,
        source_account_code=data.source_account_code,
        source_account_name=data.source_account_name,
        display_order=max_order + 1,
    )
    db.add(adj)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="adjustment_item",
            entity_id=adj.id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "category": adj.category.value,
                "amount": str(adj.amount),
                "description": adj.description,
            },
        )
    )
    db.commit()
    db.refresh(adj)
    return adj


def update_adjustment(
    db: Session,
    deal_id: uuid.UUID,
    adjustment_id: uuid.UUID,
    data: AdjustmentItemUpdate,
) -> AdjustmentItem:
    """조정항목을 수정한다."""
    adj = db.get(AdjustmentItem, adjustment_id)
    if not adj or adj.deal_id != deal_id:
        raise NotFoundError("AdjustmentItem", str(adjustment_id))

    old_values: dict = {}
    new_values: dict = {}

    if data.category is not None:
        old_values["category"] = adj.category.value
        adj.category = data.category
        new_values["category"] = data.category.value
    if data.description is not None:
        old_values["description"] = adj.description
        adj.description = data.description
        new_values["description"] = data.description
    if data.amount is not None:
        old_values["amount"] = str(adj.amount)
        adj.amount = data.amount
        new_values["amount"] = str(data.amount)
    if data.status is not None:
        old_values["status"] = adj.status.value
        adj.status = data.status
        new_values["status"] = data.status.value
    if data.rejection_reason is not None:
        adj.rejection_reason = data.rejection_reason
        new_values["rejection_reason"] = data.rejection_reason

    if new_values:
        db.flush()
        db.add(
            AuditLog(
                deal_id=deal_id,
                entity_type="adjustment_item",
                entity_id=adj.id,
                action=AuditAction.UPDATE,
                actor="system",
                old_value=old_values,
                new_value=new_values,
            )
        )
    db.commit()
    db.refresh(adj)
    return adj


def approve_adjustment(
    db: Session,
    deal_id: uuid.UUID,
    adjustment_id: uuid.UUID,
    data: AdjustmentItemApprove,
) -> AdjustmentItem:
    """조정항목을 승인한다."""
    adj = db.get(AdjustmentItem, adjustment_id)
    if not adj or adj.deal_id != deal_id:
        raise NotFoundError("AdjustmentItem", str(adjustment_id))

    old_status = adj.status.value
    adj.status = AdjustmentStatus.APPROVED
    adj.approved_by = data.approved_by
    adj.approved_at = datetime.now(UTC)

    db.flush()
    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="adjustment_item",
            entity_id=adj.id,
            action=AuditAction.APPROVE,
            actor=data.approved_by,
            old_value={"status": old_status},
            new_value={"status": AdjustmentStatus.APPROVED.value},
        )
    )
    db.commit()
    db.refresh(adj)
    return adj


# ── Query ────────────────────────────────────────────────


def get_qoe_calculation(
    db: Session,
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID | None = None,
) -> QoECalculation | None:
    """QoE 계산 결과를 조회한다. qoe_id 없으면 최신 결과."""
    if qoe_id:
        qoe = db.get(QoECalculation, qoe_id)
        if qoe and qoe.deal_id == deal_id:
            return qoe
        return None

    stmt = (
        select(QoECalculation)
        .where(QoECalculation.deal_id == deal_id)
        .order_by(QoECalculation.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def list_qoe_calculations(
    db: Session,
    deal_id: uuid.UUID,
) -> list[QoECalculation]:
    """딜의 모든 QoE 계산 결과를 조회한다."""
    stmt = (
        select(QoECalculation)
        .where(QoECalculation.deal_id == deal_id)
        .order_by(QoECalculation.created_at.desc())
    )
    return list(db.scalars(stmt).all())
