"""NWC 계산 서비스 — FDD-601/602/603 오케스트레이션.

DB에서 데이터 조회 -> 엔진 호출 -> 결과 저장.
Sprint 14: multi-period TB 지원 (monthly_amounts 자동 집계).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ErrorCode
from app.core.exceptions import CalculationError, NotFoundError
from app.core.logging import get_logger
from app.engines.nwc_engine import (
    ENGINE_VERSION,
    BSAccountData,
    NWCDefinition,
    calculate_nwc,
    calculate_peg,
    classify_nwc_items,
    simulate_all_pegs,
)
from app.industry import get_fdd_industry_module_safe
from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.audit import AuditAction, AuditLog
from app.models.deal import Deal
from app.models.evidence import EvidenceLink, SourceType
from app.models.journal_entry import JournalEntry
from app.models.nwc import (
    NWCCalculation,
    NWCClassification,
    NWCLineItem,
    NWCStatus,
    PegMethod,
)
from app.models.standard_line_item import FinancialStatement, StandardLineItem
from app.schemas.nwc import NWCLineItemUpdate

logger = get_logger(__name__)


# -- Internal Helpers -----------------------------------------------


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


def _get_tb_monthly_amounts(
    db: Session,
    deal_id: uuid.UUID,
    entity_id: uuid.UUID | None = None,
) -> dict[str, dict[str, Decimal]]:
    """TB 계정별 월별 잔액 맵. {account_code: {YYYY-MM: balance}}.

    entry_date 기준으로 월을 결정. entry_date가 없으면 최신 잔액으로만 취급.
    """
    stmt = select(JournalEntry).where(
        JournalEntry.deal_id == deal_id,
        JournalEntry.source_type == "TB",
    )
    if entity_id is not None:
        stmt = stmt.where(JournalEntry.entity_id == entity_id)
    entries = list(db.scalars(stmt))

    monthly: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for e in entries:
        if not e.account_code:
            continue
        balance = e.balance or Decimal("0")

        if e.entry_date:
            month_key = e.entry_date.strftime("%Y-%m")
            monthly[e.account_code][month_key] += balance
        # entry_date 없는 경우: 월별 집계에 포함하지 않음 (총 잔액에만 반영)

    return dict(monthly)


def _get_line_items_map(db: Session) -> dict[str, StandardLineItem]:
    items = list(db.scalars(select(StandardLineItem)))
    return {item.code: item for item in items}


def _build_bs_accounts(
    db: Session,
    deal_id: uuid.UUID,
) -> list[BSAccountData]:
    """APPROVED 매핑 기준으로 BS 계정 데이터를 구성한다.

    Multi-period 지원: entry_date로 월별 잔액 자동 집계.
    """
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
        from app.services.fx.fx_aware_tb import (
            get_tb_accounts_fx_aware,
            get_tb_monthly_amounts_fx_aware,
        )

        tb_map = get_tb_accounts_fx_aware(db, deal_id, deal)
        monthly_map = get_tb_monthly_amounts_fx_aware(db, deal_id, deal)
    else:
        tb_map = _get_tb_accounts(db, deal_id)
        monthly_map = _get_tb_monthly_amounts(db, deal_id)
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
        monthly_amounts = monthly_map.get(mapping.source_account_code, {})

        accounts.append(
            BSAccountData(
                account_code=mapping.source_account_code,
                account_name=mapping.source_account_name,
                category=li.category.value,
                amount=balance,
                upload_file_id=str(mapping.id),
                monthly_amounts=monthly_amounts,
            )
        )

    period_count = len({m for amounts in monthly_map.values() for m in amounts})
    logger.info(
        "BS accounts built for NWC",
        extra={
            "ctx": {
                "deal_id": str(deal_id),
                "account_count": len(accounts),
                "period_count": period_count,
            }
        },
    )

    return accounts


# -- Main NWC Calculation -------------------------------------------


def run_nwc_calculation(
    db: Session,
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    peg_method: str = "LTM_AVERAGE",
    custom_peg_value: Decimal | None = None,
) -> NWCCalculation:
    """NWC 계산을 실행하고 결과를 저장한다.

    1. APPROVED 매핑 기준으로 BS 계정 구성
    2. WC 항목 분류 (순수 엔진)
    3. NWC 계산 + 월별 트렌드 (순수 엔진)
    4. Peg 산정 (순수 엔진)
    5. DB에 결과 저장 + AuditLog + EvidenceLinks
    """
    # 1. Build BS account data
    bs_accounts = _build_bs_accounts(db, deal_id)
    if not bs_accounts:
        raise CalculationError(
            ErrorCode.NWC_DEFINITION_MISSING,
            "No approved BS mappings found. Complete account mapping first.",
        )

    # 2. Classify items (pure engine)
    definition = NWCDefinition()  # v1: default classification
    items, evidence_data = classify_nwc_items(bs_accounts, definition)

    # 3. Calculate NWC (pure engine, with industry context)
    deal = db.get(Deal, deal_id)
    industry_ctx = None
    if deal and deal.industry:
        industry_module = get_fdd_industry_module_safe(deal.industry.value)
        industry_ctx = industry_module.get_context()

    nwc_result = calculate_nwc(items, industry_context=industry_ctx)

    # 4. Calculate Peg (pure engine)
    monthly_nwc: dict[str, Decimal] = {}
    for month, data in nwc_result.monthly_trend.items():
        monthly_nwc[month] = Decimal(data["nwc"])
    peg_result = calculate_peg(monthly_nwc, peg_method, custom_peg_value)

    # 5. Persist NWCCalculation
    nwc_calc = NWCCalculation(
        deal_id=deal_id,
        snapshot_id=snapshot_id,
        total_current_assets=nwc_result.total_current_assets,
        total_current_liabilities=nwc_result.total_current_liabilities,
        net_working_capital=nwc_result.net_working_capital,
        peg_method=PegMethod(peg_method),
        peg_target=peg_result.target_nwc,
        peg_delta=peg_result.delta,
        monthly_trend=nwc_result.monthly_trend,
        category_breakdown=nwc_result.category_breakdown,
        engine_version=ENGINE_VERSION,
        status=NWCStatus.DRAFT,
    )
    db.add(nwc_calc)
    db.flush()

    # 6. Persist NWC line items
    for i, item in enumerate(nwc_result.items):
        li = NWCLineItem(
            nwc_calculation_id=nwc_calc.id,
            deal_id=deal_id,
            account_code=item.account_code,
            account_name=item.account_name,
            line_item_category=item.category,
            classification=NWCClassification(item.classification),
            amount=item.amount,
            monthly_amounts=item.monthly_amounts,
            display_order=i,
        )
        db.add(li)

    # 7. AuditLog
    db.flush()
    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="nwc_calculation",
            entity_id=nwc_calc.id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "net_working_capital": str(nwc_result.net_working_capital),
                "peg_method": peg_method,
                "peg_target": str(peg_result.target_nwc),
                "item_count": len(nwc_result.items),
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
            target_id=nwc_calc.id,
            source_type=SourceType.TB,
            source_id=ev.source_id,
            source_detail=ev.source_detail,
            engine_version=ENGINE_VERSION,
            snapshot_id=snapshot_id,
        )
        db.add(link)

    db.commit()
    db.refresh(nwc_calc)
    return nwc_calc


# -- Peg Recalculation ---------------------------------------------


def recalculate_peg(
    db: Session,
    nwc_id: uuid.UUID,
    peg_method: str,
    custom_value: Decimal | None = None,
) -> NWCCalculation:
    """Peg 방법 변경 후 재계산한다."""
    nwc = db.get(NWCCalculation, nwc_id)
    if not nwc:
        raise NotFoundError("NWCCalculation", str(nwc_id))

    monthly_nwc: dict[str, Decimal] = {}
    for month, data in nwc.monthly_trend.items():
        monthly_nwc[month] = Decimal(data["nwc"])

    peg_result = calculate_peg(monthly_nwc, peg_method, custom_value)

    old_method = nwc.peg_method.value
    nwc.peg_method = PegMethod(peg_method)
    nwc.peg_target = peg_result.target_nwc
    nwc.peg_delta = peg_result.delta

    db.flush()
    db.add(
        AuditLog(
            deal_id=nwc.deal_id,
            entity_type="nwc_calculation",
            entity_id=nwc.id,
            action=AuditAction.UPDATE,
            actor="system",
            old_value={"peg_method": old_method},
            new_value={
                "peg_method": peg_method,
                "peg_target": str(peg_result.target_nwc),
                "peg_delta": str(peg_result.delta),
            },
        )
    )
    db.commit()
    db.refresh(nwc)
    return nwc


# -- Line Item Classification Update --------------------------------


def update_line_item_classification(
    db: Session,
    deal_id: uuid.UUID,
    line_item_id: uuid.UUID,
    data: NWCLineItemUpdate,
) -> NWCLineItem:
    """NWC 항목 분류를 변경한다 — FDD-601."""
    li = db.get(NWCLineItem, line_item_id)
    if not li or li.deal_id != deal_id:
        raise NotFoundError("NWCLineItem", str(line_item_id))

    old_classification = li.classification.value
    li.classification = data.classification

    db.flush()
    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="nwc_line_item",
            entity_id=li.id,
            action=AuditAction.UPDATE,
            actor="system",
            old_value={"classification": old_classification},
            new_value={"classification": data.classification.value},
        )
    )
    db.commit()
    db.refresh(li)
    return li


# -- Peg Simulation ------------------------------------------------


def simulate_peg_scenarios(
    db: Session,
    nwc_id: uuid.UUID,
    custom_value: Decimal | None = None,
) -> tuple[Decimal, list]:
    """6종 Peg 시나리오를 시뮬레이션한다 — FDD-603.

    Returns:
        (reference_nwc, list of PegResult)
    """
    nwc = db.get(NWCCalculation, nwc_id)
    if not nwc:
        raise NotFoundError("NWCCalculation", str(nwc_id))

    monthly_nwc: dict[str, Decimal] = {}
    for month, data in nwc.monthly_trend.items():
        monthly_nwc[month] = Decimal(data["nwc"])

    results = simulate_all_pegs(monthly_nwc, custom_value)
    return nwc.net_working_capital, results


# -- Query ----------------------------------------------------------


def get_nwc_calculation(
    db: Session,
    deal_id: uuid.UUID,
    nwc_id: uuid.UUID | None = None,
) -> NWCCalculation | None:
    if nwc_id:
        nwc = db.get(NWCCalculation, nwc_id)
        if nwc and nwc.deal_id == deal_id:
            return nwc
        return None

    stmt = (
        select(NWCCalculation)
        .where(NWCCalculation.deal_id == deal_id)
        .order_by(NWCCalculation.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def list_nwc_calculations(
    db: Session,
    deal_id: uuid.UUID,
) -> list[NWCCalculation]:
    stmt = (
        select(NWCCalculation)
        .where(NWCCalculation.deal_id == deal_id)
        .order_by(NWCCalculation.created_at.desc())
    )
    return list(db.scalars(stmt).all())
