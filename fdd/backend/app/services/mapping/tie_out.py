"""IS/BS Tie-out 검증 서비스 — FDD-303.

APPROVED 매핑 기준으로 IS/BS를 재구성하고,
TB 합계와 비교하여 불일치 여부를 검증한다.
tie-out 결과는 품질 게이트로 저장.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.journal_entry import JournalEntry
from app.models.standard_line_item import FinancialStatement, StandardLineItem
from app.models.tie_out import TieOutResult, TieOutStatus


def _get_tb_accounts(
    db: Session,
    deal_id: uuid.UUID,
) -> dict[str, Decimal]:
    """TB 계정별 잔액 맵을 반환한다. {account_code: balance}."""
    stmt = select(JournalEntry).where(
        JournalEntry.deal_id == deal_id,
        JournalEntry.source_type == "TB",
    )
    entries = list(db.scalars(stmt))

    tb_map: dict[str, Decimal] = {}
    for entry in entries:
        if entry.account_code:
            balance = entry.balance or Decimal("0")
            tb_map[entry.account_code] = (
                tb_map.get(entry.account_code, Decimal("0")) + balance
            )

    return tb_map


def _get_line_items_map(db: Session) -> dict[str, StandardLineItem]:
    """표준 라인아이템 코드 → 객체 맵."""
    stmt = select(StandardLineItem)
    items = list(db.scalars(stmt))
    return {item.code: item for item in items}


def reconstruct_statements(
    db: Session,
    deal_id: uuid.UUID,
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """APPROVED 매핑 기준으로 IS/BS를 재구성한다.

    Returns:
        (is_totals, bs_totals) — {line_item_code: 금액 합계}
    """
    stmt = select(AccountMapping).where(
        AccountMapping.deal_id == deal_id,
        AccountMapping.status == MappingStatus.APPROVED,
    )
    mappings = list(db.scalars(stmt))

    tb_map = _get_tb_accounts(db, deal_id)
    line_items_map = _get_line_items_map(db)

    is_totals: dict[str, Decimal] = {}
    bs_totals: dict[str, Decimal] = {}

    for mapping in mappings:
        balance = tb_map.get(mapping.source_account_code, Decimal("0"))
        line_item = line_items_map.get(mapping.target_line_item_code)
        if not line_item:
            continue

        if line_item.statement_type == FinancialStatement.IS:
            is_totals[line_item.code] = (
                is_totals.get(line_item.code, Decimal("0")) + balance
            )
        else:
            bs_totals[line_item.code] = (
                bs_totals.get(line_item.code, Decimal("0")) + balance
            )

    return is_totals, bs_totals


def _calculate_tb_totals_by_statement(
    db: Session,
    deal_id: uuid.UUID,
) -> tuple[Decimal, Decimal, Decimal, int]:
    """TB에서 매핑/미매핑 합계를 계산한다.

    Returns:
        (mapped_is_total, mapped_bs_total, unmapped_total, unmapped_count)
    """
    tb_map = _get_tb_accounts(db, deal_id)

    stmt = select(AccountMapping).where(AccountMapping.deal_id == deal_id)
    all_mappings = list(db.scalars(stmt))
    mapped_codes = {m.source_account_code for m in all_mappings}

    line_items_map = _get_line_items_map(db)

    mapped_is = Decimal("0")
    mapped_bs = Decimal("0")
    unmapped_total = Decimal("0")
    unmapped_count = 0

    for code, balance in tb_map.items():
        if code not in mapped_codes:
            unmapped_total += balance
            unmapped_count += 1
            continue

        # 매핑된 계정의 statement_type 확인
        mapping = next((m for m in all_mappings if m.source_account_code == code), None)
        if mapping:
            li = line_items_map.get(mapping.target_line_item_code)
            if li and li.statement_type == FinancialStatement.IS:
                mapped_is += balance
            elif li:
                mapped_bs += balance

    return mapped_is, mapped_bs, unmapped_total, unmapped_count


def _find_top_discrepancies(
    totals: dict[str, Decimal],
    line_items_map: dict[str, StandardLineItem],
    limit: int = 20,
) -> list[dict]:
    """금액 절대값 기준 Top N 항목을 반환한다."""
    items = []
    for code, amount in totals.items():
        li = line_items_map.get(code)
        items.append(
            {
                "code": code,
                "name_en": li.name_en if li else code,
                "name_ko": li.name_ko if li else code,
                "amount": str(amount),
            }
        )

    items.sort(key=lambda x: abs(Decimal(x["amount"])), reverse=True)
    return items[:limit]


def validate_tie_out(
    db: Session,
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    tolerance_percentage: Decimal = Decimal("0.01"),
) -> tuple[TieOutResult, TieOutResult]:
    """IS/BS Tie-out 검증을 실행한다.

    Args:
        db: DB 세션.
        deal_id: 딜 ID.
        snapshot_id: 스냅샷 ID.
        tolerance_percentage: 허용 오차 (%, 기본 0.01%).

    Returns:
        (is_result, bs_result) TieOutResult 튜플.
    """
    # 재구성 합계
    is_totals, bs_totals = reconstruct_statements(db, deal_id)
    is_reconstructed = sum(is_totals.values(), Decimal("0"))
    bs_reconstructed = sum(bs_totals.values(), Decimal("0"))

    # TB 기준 합계
    mapped_is, mapped_bs, unmapped_total, unmapped_count = (
        _calculate_tb_totals_by_statement(db, deal_id)
    )

    line_items_map = _get_line_items_map(db)

    # IS Tie-out
    is_variance = is_reconstructed - mapped_is
    is_variance_pct = (
        (is_variance / mapped_is * Decimal("100"))
        if mapped_is != Decimal("0")
        else Decimal("0")
    )
    is_status = (
        TieOutStatus.PASS
        if abs(is_variance_pct) <= tolerance_percentage
        else TieOutStatus.FAIL
    )
    if unmapped_count > 0 and is_status == TieOutStatus.PASS:
        is_status = TieOutStatus.WARNING

    is_result = TieOutResult(
        deal_id=deal_id,
        snapshot_id=snapshot_id,
        statement_type=FinancialStatement.IS,
        status=is_status,
        tb_total=mapped_is,
        reconstructed_total=is_reconstructed,
        variance=is_variance,
        variance_percentage=abs(is_variance_pct),
        unmapped_account_count=unmapped_count,
        unmapped_total=unmapped_total,
        top_discrepancies=_find_top_discrepancies(is_totals, line_items_map),
    )

    # BS Tie-out
    bs_variance = bs_reconstructed - mapped_bs
    bs_variance_pct = (
        (bs_variance / mapped_bs * Decimal("100"))
        if mapped_bs != Decimal("0")
        else Decimal("0")
    )
    bs_status = (
        TieOutStatus.PASS
        if abs(bs_variance_pct) <= tolerance_percentage
        else TieOutStatus.FAIL
    )
    if unmapped_count > 0 and bs_status == TieOutStatus.PASS:
        bs_status = TieOutStatus.WARNING

    bs_result = TieOutResult(
        deal_id=deal_id,
        snapshot_id=snapshot_id,
        statement_type=FinancialStatement.BS,
        status=bs_status,
        tb_total=mapped_bs,
        reconstructed_total=bs_reconstructed,
        variance=bs_variance,
        variance_percentage=abs(bs_variance_pct),
        unmapped_account_count=unmapped_count,
        unmapped_total=unmapped_total,
        top_discrepancies=_find_top_discrepancies(bs_totals, line_items_map),
    )

    db.add(is_result)
    db.add(bs_result)
    db.commit()

    return is_result, bs_result
