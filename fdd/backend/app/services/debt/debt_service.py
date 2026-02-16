"""Net Debt 계산 서비스 — FDD-701/702/703/704 오케스트레이션.

DB에서 데이터 조회 -> 엔진 호출 -> 결과 저장.
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
from app.engines.debt_engine import (
    ENGINE_VERSION,
    BSAccountData,
    DebtOptions,
    calculate_net_debt,
    detect_debt_like_candidates,
)
from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.audit import AuditAction, AuditLog
from app.models.debt import (
    DebtItem,
    DebtItemStatus,
    DebtItemType,
    DebtStatus,
    NetDebtCalculation,
)
from app.models.evidence import EvidenceLink, SourceType
from app.models.journal_entry import JournalEntry
from app.models.standard_line_item import FinancialStatement, StandardLineItem
from app.schemas.debt import DebtItemApprove, DebtItemCreate, DebtItemUpdate

logger = get_logger(__name__)


# -- Internal Helpers -----------------------------------------------


def _get_tb_accounts(
    db: Session,
    deal_id: uuid.UUID,
    entity_id: uuid.UUID | None = None,
) -> dict[str, Decimal]:
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


def _get_line_items_map(db: Session) -> dict[str, StandardLineItem]:
    items = list(db.scalars(select(StandardLineItem)))
    return {item.code: item for item in items}


def _build_bs_accounts(
    db: Session,
    deal_id: uuid.UUID,
) -> list[BSAccountData]:
    """APPROVED 매핑 기준으로 BS 계정 데이터를 구성한다."""
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
    li_map = _get_line_items_map(db)

    accounts: list[BSAccountData] = []
    for mapping in mappings:
        li = li_map.get(mapping.target_line_item_code)
        if not li:
            continue
        if li.statement_type != FinancialStatement.BS:
            continue
        if li.is_subtotal:
            continue

        balance = tb_map.get(mapping.source_account_code, Decimal("0"))

        accounts.append(
            BSAccountData(
                account_code=mapping.source_account_code,
                account_name=mapping.source_account_name,
                category=li.category.value,
                amount=balance,
                upload_file_id=str(mapping.id),
            )
        )

    return accounts


# -- Main Net Debt Calculation ---------------------------------------


def run_net_debt_calculation(
    db: Session,
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    include_lease_liabilities: bool = False,
    include_deferred_revenue: bool = False,
) -> NetDebtCalculation:
    """Net Debt 계산을 실행하고 결과를 저장한다.

    1. APPROVED 매핑 기준으로 BS 계정 구성
    2. Net Debt 계산 (순수 엔진)
    3. Debt-like 후보 탐지 (순수 엔진)
    4. DB에 결과 저장 + AuditLog + EvidenceLinks
    """
    # 1. Build BS account data
    bs_accounts = _build_bs_accounts(db, deal_id)
    if not bs_accounts:
        raise CalculationError(
            ErrorCode.DEBT_CLASSIFICATION_INCOMPLETE,
            "No approved BS mappings found. Complete account mapping first.",
        )

    # 2. Calculate Net Debt (pure engine)
    options = DebtOptions(
        include_lease_liabilities=include_lease_liabilities,
        include_deferred_revenue=include_deferred_revenue,
    )
    debt_result, evidence_data = calculate_net_debt(bs_accounts, options)

    # 3. Detect debt-like candidates (pure engine, with industry context)
    deal = db.get(Deal, deal_id)
    industry_ctx = None
    if deal and deal.industry:
        industry_module = get_fdd_industry_module_safe(deal.industry.value)
        industry_ctx = industry_module.get_context()

    candidates = detect_debt_like_candidates(bs_accounts, industry_context=industry_ctx)

    # 4. Persist NetDebtCalculation
    calc = NetDebtCalculation(
        deal_id=deal_id,
        snapshot_id=snapshot_id,
        gross_debt=debt_result.gross_debt,
        cash_and_equivalents=debt_result.cash_and_equivalents,
        net_debt=debt_result.net_debt,
        debt_like_total=debt_result.debt_like_total,
        cash_like_total=debt_result.cash_like_total,
        adjusted_net_debt=debt_result.adjusted_net_debt,
        include_lease_liabilities=include_lease_liabilities,
        include_deferred_revenue=include_deferred_revenue,
        balance_check_error=debt_result.balance_check_error,
        category_breakdown=debt_result.category_breakdown,
        engine_version=ENGINE_VERSION,
        status=DebtStatus.DRAFT,
    )
    db.add(calc)
    db.flush()

    # 5. Persist classified items (from engine result)
    for i, item in enumerate(debt_result.items):
        di = DebtItem(
            net_debt_calculation_id=calc.id,
            deal_id=deal_id,
            item_type=DebtItemType(item.item_type),
            description=item.description,
            amount=item.amount,
            source_account_code=item.source_account_code,
            source_account_name=item.source_account_name,
            detection_method=item.detection_method,
            confidence_score=item.confidence_score,
            status=DebtItemStatus.CANDIDATE,
            display_order=i,
        )
        db.add(di)

    # 6. Persist debt-like candidates (that aren't already classified)
    existing_codes = {item.source_account_code for item in debt_result.items}
    offset = len(debt_result.items)
    for j, cand in enumerate(candidates):
        if cand.source_account_code in existing_codes:
            continue
        di = DebtItem(
            net_debt_calculation_id=calc.id,
            deal_id=deal_id,
            item_type=DebtItemType(cand.item_type),
            description=cand.description,
            amount=cand.amount,
            source_account_code=cand.source_account_code,
            source_account_name=cand.source_account_name,
            detection_method=cand.detection_method,
            confidence_score=cand.confidence_score,
            status=DebtItemStatus.CANDIDATE,
            display_order=offset + j,
        )
        db.add(di)

    # 7. AuditLog
    db.flush()
    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="net_debt_calculation",
            entity_id=calc.id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "net_debt": str(debt_result.net_debt),
                "adjusted_net_debt": str(debt_result.adjusted_net_debt),
                "item_count": len(debt_result.items),
                "candidate_count": len(candidates),
                "engine_version": ENGINE_VERSION,
            },
        )
    )

    # 8. EvidenceLinks
    for ev in evidence_data:
        if not ev.source_id:
            continue
        link = EvidenceLink(
            deal_id=deal_id,
            target_type=ev.target_type,
            target_id=calc.id,
            source_type=SourceType.TB,
            source_id=ev.source_id,
            source_detail=ev.source_detail,
            engine_version=ENGINE_VERSION,
            snapshot_id=snapshot_id,
        )
        db.add(link)

    db.commit()
    db.refresh(calc)
    return calc


# -- Recalculate with Options ----------------------------------------


def recalculate_net_debt(
    db: Session,
    calc_id: uuid.UUID,
    include_lease_liabilities: bool | None = None,
    include_deferred_revenue: bool | None = None,
) -> NetDebtCalculation:
    """옵션 변경 후 Net Debt를 재계산한다."""
    calc = db.get(NetDebtCalculation, calc_id)
    if not calc:
        raise NotFoundError("NetDebtCalculation", str(calc_id))

    # APPROVED items만 합산하여 재계산
    approved_items = [i for i in calc.items if i.status == DebtItemStatus.APPROVED]

    gross_debt = Decimal("0")
    cash = Decimal("0")
    debt_like = Decimal("0")
    cash_like = Decimal("0")

    for item in approved_items:
        if item.item_type == DebtItemType.GROSS_DEBT:
            gross_debt += item.amount
        elif item.item_type == DebtItemType.CASH:
            cash += item.amount
        elif item.item_type == DebtItemType.DEBT_LIKE:
            debt_like += item.amount
        elif item.item_type == DebtItemType.CASH_LIKE:
            cash_like += item.amount

    from app.engines.debt_engine import _q

    gross_debt = _q(gross_debt)
    cash = _q(cash)
    debt_like = _q(debt_like)
    cash_like = _q(cash_like)
    net_debt = _q(gross_debt - cash)
    adjusted = _q(net_debt + debt_like - cash_like)
    balance_error = _q(gross_debt - cash + debt_like - cash_like - adjusted)

    old_adjusted = str(calc.adjusted_net_debt)
    calc.gross_debt = gross_debt
    calc.cash_and_equivalents = cash
    calc.net_debt = net_debt
    calc.debt_like_total = debt_like
    calc.cash_like_total = cash_like
    calc.adjusted_net_debt = adjusted
    calc.balance_check_error = balance_error

    if include_lease_liabilities is not None:
        calc.include_lease_liabilities = include_lease_liabilities
    if include_deferred_revenue is not None:
        calc.include_deferred_revenue = include_deferred_revenue

    db.flush()
    db.add(
        AuditLog(
            deal_id=calc.deal_id,
            entity_type="net_debt_calculation",
            entity_id=calc.id,
            action=AuditAction.UPDATE,
            actor="system",
            old_value={"adjusted_net_debt": old_adjusted},
            new_value={
                "adjusted_net_debt": str(adjusted),
                "approved_count": len(approved_items),
            },
        )
    )
    db.commit()
    db.refresh(calc)
    return calc


# -- Debt Item CRUD --------------------------------------------------


def add_manual_debt_item(
    db: Session,
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    data: DebtItemCreate,
) -> DebtItem:
    calc = db.get(NetDebtCalculation, calc_id)
    if not calc or calc.deal_id != deal_id:
        raise NotFoundError("NetDebtCalculation", str(calc_id))

    max_order = max((i.display_order for i in calc.items), default=-1)
    item = DebtItem(
        net_debt_calculation_id=calc_id,
        deal_id=deal_id,
        item_type=data.item_type,
        description=data.description,
        amount=data.amount,
        detection_method="manual",
        status=DebtItemStatus.PROPOSED,
        source_account_code=data.source_account_code,
        source_account_name=data.source_account_name,
        display_order=max_order + 1,
    )
    db.add(item)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="debt_item",
            entity_id=item.id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "item_type": item.item_type.value,
                "amount": str(item.amount),
                "description": item.description,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item


def update_debt_item(
    db: Session,
    deal_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DebtItemUpdate,
) -> DebtItem:
    item = db.get(DebtItem, item_id)
    if not item or item.deal_id != deal_id:
        raise NotFoundError("DebtItem", str(item_id))

    old_values: dict = {}
    new_values: dict = {}

    if data.item_type is not None:
        old_values["item_type"] = item.item_type.value
        item.item_type = data.item_type
        new_values["item_type"] = data.item_type.value
    if data.description is not None:
        old_values["description"] = item.description
        item.description = data.description
        new_values["description"] = data.description
    if data.amount is not None:
        old_values["amount"] = str(item.amount)
        item.amount = data.amount
        new_values["amount"] = str(data.amount)
    if data.status is not None:
        old_values["status"] = item.status.value
        item.status = data.status
        new_values["status"] = data.status.value
    if data.rejection_reason is not None:
        item.rejection_reason = data.rejection_reason
        new_values["rejection_reason"] = data.rejection_reason

    if new_values:
        db.flush()
        db.add(
            AuditLog(
                deal_id=deal_id,
                entity_type="debt_item",
                entity_id=item.id,
                action=AuditAction.UPDATE,
                actor="system",
                old_value=old_values,
                new_value=new_values,
            )
        )
    db.commit()
    db.refresh(item)
    return item


def approve_debt_item(
    db: Session,
    deal_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DebtItemApprove,
) -> DebtItem:
    item = db.get(DebtItem, item_id)
    if not item or item.deal_id != deal_id:
        raise NotFoundError("DebtItem", str(item_id))

    old_status = item.status.value
    item.status = DebtItemStatus.APPROVED
    item.approved_by = data.approved_by
    item.approved_at = datetime.now(UTC)

    db.flush()
    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="debt_item",
            entity_id=item.id,
            action=AuditAction.APPROVE,
            actor=data.approved_by,
            old_value={"status": old_status},
            new_value={"status": DebtItemStatus.APPROVED.value},
        )
    )
    db.commit()
    db.refresh(item)
    return item


# -- Query -----------------------------------------------------------


def get_net_debt_calculation(
    db: Session,
    deal_id: uuid.UUID,
    calc_id: uuid.UUID | None = None,
) -> NetDebtCalculation | None:
    if calc_id:
        calc = db.get(NetDebtCalculation, calc_id)
        if calc and calc.deal_id == deal_id:
            return calc
        return None

    stmt = (
        select(NetDebtCalculation)
        .where(NetDebtCalculation.deal_id == deal_id)
        .order_by(NetDebtCalculation.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def list_net_debt_calculations(
    db: Session,
    deal_id: uuid.UUID,
) -> list[NetDebtCalculation]:
    stmt = (
        select(NetDebtCalculation)
        .where(NetDebtCalculation.deal_id == deal_id)
        .order_by(NetDebtCalculation.created_at.desc())
    )
    return list(db.scalars(stmt).all())
