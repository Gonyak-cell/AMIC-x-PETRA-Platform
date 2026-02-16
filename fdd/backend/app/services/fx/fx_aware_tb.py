"""FX-aware TB 계정 로더 — Sprint 16.

외화 항목 존재 여부를 확인하고, 필요 시 환율 변환을 적용한다.
기존 _get_tb_accounts()/_get_tb_monthly_amounts()의 drop-in replacement.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.journal_entry import JournalEntry


def has_foreign_currency_entries(
    db: Session,
    deal_id: uuid.UUID,
    base_currency: str,
) -> bool:
    """딜에 base_currency가 아닌 TB 엔트리가 존재하는지 확인한다."""
    stmt = (
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.deal_id == deal_id,
            JournalEntry.source_type == "TB",
            JournalEntry.currency.isnot(None),
            JournalEntry.currency != base_currency,
        )
    )
    return (db.scalar(stmt) or 0) > 0


def get_tb_accounts_fx_aware(
    db: Session,
    deal_id: uuid.UUID,
    deal: Deal,
    entity_id: uuid.UUID | None = None,
) -> dict[str, Decimal]:
    """TB 계정별 잔액을 반환한다. 외화 항목이 있으면 FX 환산을 적용한다.

    Args:
        db: DB session.
        deal_id: 딜 ID.
        deal: Deal 객체 (base_currency, reference_date 필요).
        entity_id: 엔티티 ID (optional).

    Returns:
        {account_code: balance} (모두 base_currency로 환산됨).
    """
    if has_foreign_currency_entries(db, deal_id, deal.base_currency):
        from app.services.fx.fx_service import build_fx_converted_tb_map

        return build_fx_converted_tb_map(
            db,
            deal_id,
            target_currency=deal.base_currency,
            reference_date=deal.reference_date,
            entity_id=entity_id,
        )

    # 외화 없음 — 기존 로직으로 집계
    return _simple_tb_aggregation(db, deal_id, entity_id)


def get_tb_monthly_amounts_fx_aware(
    db: Session,
    deal_id: uuid.UUID,
    deal: Deal,
    entity_id: uuid.UUID | None = None,
) -> dict[str, dict[str, Decimal]]:
    """TB 계정별 월별 잔액을 반환한다. 외화 항목이 있으면 FX 환산을 적용한다.

    Returns:
        {account_code: {"YYYY-MM": balance}} (모두 base_currency로 환산됨).
    """
    if has_foreign_currency_entries(db, deal_id, deal.base_currency):
        from app.services.fx.fx_service import build_fx_converted_monthly_map

        return build_fx_converted_monthly_map(
            db,
            deal_id,
            target_currency=deal.base_currency,
            entity_id=entity_id,
        )

    # 외화 없음 — 기존 로직으로 집계
    return _simple_monthly_aggregation(db, deal_id, entity_id)


def _simple_tb_aggregation(
    db: Session,
    deal_id: uuid.UUID,
    entity_id: uuid.UUID | None = None,
) -> dict[str, Decimal]:
    """환율 변환 없이 TB 잔액을 집계한다."""
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


def _simple_monthly_aggregation(
    db: Session,
    deal_id: uuid.UUID,
    entity_id: uuid.UUID | None = None,
) -> dict[str, dict[str, Decimal]]:
    """환율 변환 없이 TB 월별 잔액을 집계한다."""
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

    return {k: dict(v) for k, v in monthly.items()}
