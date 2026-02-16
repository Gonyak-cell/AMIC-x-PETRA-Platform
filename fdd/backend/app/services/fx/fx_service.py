"""FX 환산 서비스 — Sprint 16.

서비스 레이어에서 엔진 호출 전에 환율 변환을 수행한다.
엔진 함수는 항상 presentation currency로 변환된 데이터만 수신.
"""

import uuid
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ErrorCode
from app.core.exceptions import FDDError
from app.models.exchange_rate import ExchangeRate, RateType
from app.models.journal_entry import JournalEntry


def get_rate(
    db: Session,
    deal_id: uuid.UUID,
    from_currency: str,
    to_currency: str,
    rate_type: RateType,
    effective_date: date | None = None,
    period_key: str | None = None,
) -> Decimal:
    """환율을 조회한다. 없으면 FDDError 발생."""
    if from_currency == to_currency:
        return Decimal("1.0000")

    stmt = select(ExchangeRate).where(
        ExchangeRate.deal_id == deal_id,
        ExchangeRate.from_currency == from_currency,
        ExchangeRate.to_currency == to_currency,
        ExchangeRate.rate_type == rate_type,
    )

    if period_key and rate_type == RateType.AVERAGE:
        stmt = stmt.where(ExchangeRate.period_key == period_key)
    elif effective_date:
        stmt = stmt.where(ExchangeRate.effective_date <= effective_date)
        stmt = stmt.order_by(ExchangeRate.effective_date.desc())

    rate_record = db.scalars(stmt).first()
    if rate_record is None:
        raise FDDError(
            ErrorCode.INGEST_FX_RATE_MISSING,
            detail=(
                f"Exchange rate not found: {from_currency}/{to_currency} "
                f"({rate_type.value}) at {effective_date or period_key}"
            ),
        )
    return rate_record.rate


def convert_amount(amount: Decimal, rate: Decimal) -> Decimal:
    """금액을 환율로 변환한다 (pure function).

    Returns:
        변환된 금액 (소수점 4자리).
    """
    return (amount * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def build_fx_converted_tb_map(
    db: Session,
    deal_id: uuid.UUID,
    target_currency: str,
    reference_date: date | None = None,
    entity_id: uuid.UUID | None = None,
) -> dict[str, Decimal]:
    """TB 계정별 잔액을 target_currency로 변환하여 반환한다.

    BS 항목은 CLOSING 환율, 이미 target_currency인 항목은 변환하지 않는다.

    Returns:
        {account_code: converted_balance}
    """
    stmt = select(JournalEntry).where(
        JournalEntry.deal_id == deal_id,
        JournalEntry.source_type == "TB",
    )
    if entity_id is not None:
        stmt = stmt.where(JournalEntry.entity_id == entity_id)

    entries = list(db.scalars(stmt))

    # 환율 캐시 {(from_currency, rate_type): rate}
    rate_cache: dict[tuple[str, RateType], Decimal] = {}
    result: dict[str, Decimal] = defaultdict(Decimal)

    for entry in entries:
        if not entry.account_code:
            continue

        balance = entry.balance or Decimal("0")
        currency = entry.currency or target_currency

        if currency == target_currency:
            result[entry.account_code] += balance
            continue

        cache_key = (currency, RateType.CLOSING)
        if cache_key not in rate_cache:
            rate_cache[cache_key] = get_rate(
                db,
                deal_id,
                from_currency=currency,
                to_currency=target_currency,
                rate_type=RateType.CLOSING,
                effective_date=reference_date,
            )

        converted = convert_amount(balance, rate_cache[cache_key])
        result[entry.account_code] += converted

    return dict(result)


def build_fx_converted_monthly_map(
    db: Session,
    deal_id: uuid.UUID,
    target_currency: str,
    entity_id: uuid.UUID | None = None,
) -> dict[str, dict[str, Decimal]]:
    """TB 계정별 월별 잔액을 target_currency로 변환하여 반환한다.

    Returns:
        {account_code: {"2025-01": converted_balance, ...}}
    """
    stmt = select(JournalEntry).where(
        JournalEntry.deal_id == deal_id,
        JournalEntry.source_type == "TB",
    )
    if entity_id is not None:
        stmt = stmt.where(JournalEntry.entity_id == entity_id)

    entries = list(db.scalars(stmt))

    rate_cache: dict[tuple[str, RateType, str | None], Decimal] = {}
    monthly: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for entry in entries:
        if not entry.account_code or not entry.entry_date:
            continue

        balance = entry.balance or Decimal("0")
        currency = entry.currency or target_currency
        month_key = entry.entry_date.strftime("%Y-%m")

        if currency == target_currency:
            monthly[entry.account_code][month_key] += balance
            continue

        cache_key = (currency, RateType.CLOSING, month_key)
        if cache_key not in rate_cache:
            try:
                rate_cache[cache_key] = get_rate(
                    db,
                    deal_id,
                    from_currency=currency,
                    to_currency=target_currency,
                    rate_type=RateType.CLOSING,
                    effective_date=entry.entry_date,
                )
            except FDDError:
                # 월별 환율 없으면 skip
                continue

        converted = convert_amount(balance, rate_cache[cache_key])
        monthly[entry.account_code][month_key] += converted

    return {k: dict(v) for k, v in monthly.items()}
