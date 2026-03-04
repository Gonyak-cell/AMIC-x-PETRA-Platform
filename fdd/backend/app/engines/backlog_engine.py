"""수주잔액(Order Backlog) 분석 엔진.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.

Big 4 WP 수준의 수주잔액 분석:
- 수주잔액 Summary (총잔액, Book-to-Bill, 커버리지 개월수)
- 거래처별 수주잔액 (비중, 집중도)
- 수주 Aging (0-3M / 3-6M / 6-12M / 12M+)
- 역마진 수주 감지 (원가 > 수주금액)
- 월별 신규수주 추이
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ENGINE_VERSION = "0.1.0"

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


def _pct(value: Decimal) -> Decimal:
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class EvidenceLinkData:
    target_type: str
    source_type: str
    source_id: str
    source_detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class BacklogCustomerItem:
    """거래처별 수주잔액."""

    customer_name: str
    amount: Decimal
    share_pct: Decimal  # 비중 (%)
    order_count: int = 0
    aging_bucket: str = ""  # 대표 aging 구간


@dataclass(frozen=True)
class BacklogAgingBucket:
    """Aging 구간별 수주잔액."""

    bucket: str  # "0-3M", "3-6M", "6-12M", "12M+"
    amount: Decimal
    share_pct: Decimal
    order_count: int = 0


@dataclass(frozen=True)
class NegativeMarginOrder:
    """역마진 수주."""

    order_id: str
    customer_name: str
    order_amount: Decimal
    estimated_cost: Decimal
    margin: Decimal  # (amount - cost) / amount * 100
    reason: str = ""


@dataclass
class BacklogSummaryResult:
    """수주잔액 Summary 결과."""

    total_backlog: Decimal
    backlog_by_customer: list[BacklogCustomerItem]
    book_to_bill_ratio: Decimal | None  # 신규수주 / 매출
    backlog_coverage_months: Decimal | None  # 잔액 / 월평균매출
    top_n_share: Decimal  # Top 5 비중 (%)
    concentration_index: Decimal  # HHI (0~10000)
    order_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class BacklogAgingResult:
    """수주 Aging 분석 결과."""

    total_backlog: Decimal
    buckets: list[BacklogAgingBucket]
    overdue_amount: Decimal  # 납기 초과 금액
    overdue_share_pct: Decimal  # 납기 초과 비중 (%)
    warnings: list[str] = field(default_factory=list)


@dataclass
class NegativeMarginResult:
    """역마진 분석 결과."""

    negative_margin_orders: list[NegativeMarginOrder]
    total_negative_amount: Decimal  # 역마진 수주 총액
    total_negative_loss: Decimal  # 역마진 손실 추정
    negative_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class MonthlyNewOrderResult:
    """월별 신규수주 추이."""

    months: list[str]
    amounts: dict[str, Decimal]
    cumulative: dict[str, Decimal]
    yoy_growth: dict[str, Decimal]  # 전년 동월 대비 증감률
    warnings: list[str] = field(default_factory=list)


# ── Core: Backlog Summary ────────────────────────────────


def compute_backlog_summary(
    backlog_entries: list[dict[str, Any]],
    *,
    revenue_total: Decimal | None = None,
    new_orders_total: Decimal | None = None,
    revenue_months: int = 12,
    top_n: int = 5,
    customer_key: str = "customer_name",
    amount_key: str = "amount",
) -> tuple[BacklogSummaryResult, list[EvidenceLinkData]]:
    """수주잔액 Summary를 계산한다.

    Args:
        backlog_entries: 수주잔액 항목 리스트
            [{"customer_name": "A사", "amount": "50000", "order_id": "...", ...}, ...]
        revenue_total: 기간 매출 합계 (Book-to-Bill, 커버리지 계산용)
        new_orders_total: 기간 신규수주 합계 (Book-to-Bill 계산용)
        revenue_months: 매출 기간 월수 (커버리지 계산용, 기본 12)
        top_n: Top N 거래처 수 (기본 5)

    Returns:
        (BacklogSummaryResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    if not backlog_entries:
        return BacklogSummaryResult(
            total_backlog=ZERO,
            backlog_by_customer=[],
            book_to_bill_ratio=None,
            backlog_coverage_months=None,
            top_n_share=ZERO,
            concentration_index=ZERO,
            warnings=["BACKLOG_EMPTY: No backlog data"],
        ), evidence

    # 거래처별 집계
    customer_totals: dict[str, Decimal] = {}
    customer_counts: dict[str, int] = {}

    for e in backlog_entries:
        cust = str(e.get(customer_key, "기타")).strip() or "기타"
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO

        customer_totals[cust] = customer_totals.get(cust, ZERO) + amount
        customer_counts[cust] = customer_counts.get(cust, 0) + 1

    total_backlog = _q(sum(customer_totals.values()))

    # 거래처별 비중 + 정렬
    sorted_customers = sorted(
        customer_totals.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    backlog_by_customer: list[BacklogCustomerItem] = []
    for cust, amount in sorted_customers:
        share = _pct(amount / total_backlog * HUNDRED) if total_backlog > ZERO else ZERO
        backlog_by_customer.append(
            BacklogCustomerItem(
                customer_name=cust,
                amount=amount,
                share_pct=share,
                order_count=customer_counts.get(cust, 0),
            )
        )

    # Top N 비중
    top_n_amount = sum(item.amount for item in backlog_by_customer[:top_n])
    top_n_share = (
        _pct(top_n_amount / total_backlog * HUNDRED) if total_backlog > ZERO else ZERO
    )

    # HHI (Herfindahl-Hirschman Index)
    hhi = ZERO
    if total_backlog > ZERO:
        for item in backlog_by_customer:
            share_frac = item.amount / total_backlog * HUNDRED
            hhi += share_frac * share_frac
    hhi = _pct(hhi)

    # Book-to-Bill ratio
    btb: Decimal | None = None
    if (
        new_orders_total is not None
        and revenue_total is not None
        and revenue_total > ZERO
    ):
        btb = _pct(new_orders_total / revenue_total)

    # Backlog Coverage (개월수)
    coverage: Decimal | None = None
    if revenue_total is not None and revenue_total > ZERO and revenue_months > 0:
        monthly_rev = revenue_total / Decimal(str(revenue_months))
        coverage = _pct(total_backlog / monthly_rev)

    # 경고
    if top_n_share > Decimal("80"):
        warnings.append(
            f"BACKLOG_CONCENTRATION: Top {top_n} customers account for {top_n_share}% of backlog"
        )
    if hhi > Decimal("2500"):
        warnings.append(f"BACKLOG_HIGH_HHI: HHI {hhi} indicates high concentration")
    if btb is not None and btb < Decimal("1.00"):
        warnings.append(
            f"BACKLOG_LOW_BTB: Book-to-Bill {btb} < 1.0 indicates declining order intake"
        )

    evidence.append(
        EvidenceLinkData(
            target_type="backlog_summary",
            source_type="computed",
            source_id="backlog:summary",
            source_detail={
                "total_backlog": str(total_backlog),
                "customer_count": len(backlog_by_customer),
                "top_n_share": str(top_n_share),
                "hhi": str(hhi),
            },
        )
    )

    return BacklogSummaryResult(
        total_backlog=total_backlog,
        backlog_by_customer=backlog_by_customer,
        book_to_bill_ratio=btb,
        backlog_coverage_months=coverage,
        top_n_share=top_n_share,
        concentration_index=hhi,
        order_count=len(backlog_entries),
        warnings=warnings,
    ), evidence


# ── Core: Backlog Aging ──────────────────────────────────


_DEFAULT_AGING_BUCKETS = [
    ("0-3M", 0, 3),
    ("3-6M", 3, 6),
    ("6-12M", 6, 12),
    ("12M+", 12, 9999),
]


def compute_backlog_aging(
    backlog_entries: list[dict[str, Any]],
    *,
    remaining_months_key: str = "remaining_months",
    amount_key: str = "amount",
    aging_buckets: list[tuple[str, int, int]] | None = None,
) -> tuple[BacklogAgingResult, list[EvidenceLinkData]]:
    """수주잔액 Aging 분석을 수행한다.

    Args:
        backlog_entries: 수주잔액 항목 리스트
            [{"amount": "50000", "remaining_months": 2, ...}, ...]
            remaining_months: 납기까지 남은 개월수 (음수 = 납기 초과)
        aging_buckets: [(label, min_months, max_months), ...]

    Returns:
        (BacklogAgingResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []
    buckets = aging_buckets or _DEFAULT_AGING_BUCKETS

    if not backlog_entries:
        return BacklogAgingResult(
            total_backlog=ZERO,
            buckets=[],
            overdue_amount=ZERO,
            overdue_share_pct=ZERO,
            warnings=["AGING_EMPTY: No backlog data for aging analysis"],
        ), evidence

    # 구간별 집계
    bucket_amounts: dict[str, Decimal] = {b[0]: ZERO for b in buckets}
    bucket_counts: dict[str, int] = {b[0]: 0 for b in buckets}
    overdue_amount = ZERO
    total = ZERO

    for e in backlog_entries:
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO
        remaining = int(e.get(remaining_months_key, 0))
        total += amount

        if remaining < 0:
            overdue_amount += amount

        # 남은 개월수 기준 구간 배정 (납기 초과도 0-3M에 포함)
        effective = max(remaining, 0)
        placed = False
        for label, min_m, max_m in buckets:
            if min_m <= effective < max_m:
                bucket_amounts[label] = bucket_amounts.get(label, ZERO) + amount
                bucket_counts[label] = bucket_counts.get(label, 0) + 1
                placed = True
                break
        if not placed and buckets:
            # 마지막 구간에 배정
            last_label = buckets[-1][0]
            bucket_amounts[last_label] = bucket_amounts.get(last_label, ZERO) + amount
            bucket_counts[last_label] = bucket_counts.get(last_label, 0) + 1

    total = _q(total)
    overdue_amount = _q(overdue_amount)

    # 결과 조립
    result_buckets: list[BacklogAgingBucket] = []
    for label, _, _ in buckets:
        amt = _q(bucket_amounts.get(label, ZERO))
        share = _pct(amt / total * HUNDRED) if total > ZERO else ZERO
        result_buckets.append(
            BacklogAgingBucket(
                bucket=label,
                amount=amt,
                share_pct=share,
                order_count=bucket_counts.get(label, 0),
            )
        )

    overdue_pct = _pct(overdue_amount / total * HUNDRED) if total > ZERO else ZERO

    # 경고
    if overdue_pct > Decimal("10"):
        warnings.append(f"AGING_HIGH_OVERDUE: {overdue_pct}% of backlog is overdue")

    long_term_pct = ZERO
    for b in result_buckets:
        if b.bucket in ("6-12M", "12M+"):
            long_term_pct += b.share_pct
    if long_term_pct > Decimal("30"):
        warnings.append(f"AGING_LONG_TERM: {long_term_pct}% of backlog is 6M+ aging")

    evidence.append(
        EvidenceLinkData(
            target_type="backlog_aging",
            source_type="computed",
            source_id="backlog:aging",
            source_detail={
                "total": str(total),
                "overdue": str(overdue_amount),
                "buckets": {b.bucket: str(b.amount) for b in result_buckets},
            },
        )
    )

    return BacklogAgingResult(
        total_backlog=total,
        buckets=result_buckets,
        overdue_amount=overdue_amount,
        overdue_share_pct=overdue_pct,
        warnings=warnings,
    ), evidence


# ── Core: Negative Margin Detection ─────────────────────


def detect_negative_margin_orders(
    backlog_entries: list[dict[str, Any]],
    *,
    amount_key: str = "amount",
    cost_key: str = "estimated_cost",
    order_id_key: str = "order_id",
    customer_key: str = "customer_name",
    reason_key: str = "reason",
) -> tuple[NegativeMarginResult, list[EvidenceLinkData]]:
    """역마진 수주를 감지한다.

    Args:
        backlog_entries: 수주 항목 리스트 (원가 정보 포함)
            [{"order_id": "ORD-001", "amount": "10000",
              "estimated_cost": "12000", "customer_name": "A사"}, ...]

    Returns:
        (NegativeMarginResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    negatives: list[NegativeMarginOrder] = []
    total_neg_amount = ZERO
    total_neg_loss = ZERO

    for e in backlog_entries:
        raw_amount = e.get(amount_key, "0")
        raw_cost = e.get(cost_key)
        if raw_cost is None:
            continue

        amount = _q(Decimal(str(raw_amount))) if raw_amount else ZERO
        cost = _q(Decimal(str(raw_cost))) if raw_cost else ZERO

        if cost > amount and amount > ZERO:
            margin = _pct((amount - cost) / amount * HUNDRED)
            negatives.append(
                NegativeMarginOrder(
                    order_id=str(e.get(order_id_key, "")),
                    customer_name=str(e.get(customer_key, "")),
                    order_amount=amount,
                    estimated_cost=cost,
                    margin=margin,
                    reason=str(e.get(reason_key, "")),
                )
            )
            total_neg_amount += amount
            total_neg_loss += cost - amount

    total_neg_amount = _q(total_neg_amount)
    total_neg_loss = _q(total_neg_loss)

    if not negatives:
        warnings.append("MARGIN_NO_NEGATIVE: No negative margin orders detected")

    if len(negatives) > 5:
        warnings.append(
            f"MARGIN_MANY_NEGATIVE: {len(negatives)} orders with negative margin"
        )

    for neg in negatives:
        evidence.append(
            EvidenceLinkData(
                target_type="negative_margin",
                source_type="computed",
                source_id=f"margin:{neg.order_id}",
                source_detail={
                    "order_id": neg.order_id,
                    "customer": neg.customer_name,
                    "amount": str(neg.order_amount),
                    "cost": str(neg.estimated_cost),
                    "margin": str(neg.margin),
                },
            )
        )

    return NegativeMarginResult(
        negative_margin_orders=negatives,
        total_negative_amount=total_neg_amount,
        total_negative_loss=total_neg_loss,
        negative_count=len(negatives),
        warnings=warnings,
    ), evidence


# ── Core: Monthly New Orders ─────────────────────────────


def compute_monthly_new_orders(
    order_entries: list[dict[str, Any]],
    *,
    month_key: str = "order_month",
    amount_key: str = "amount",
    prior_year_entries: list[dict[str, Any]] | None = None,
) -> tuple[MonthlyNewOrderResult, list[EvidenceLinkData]]:
    """월별 신규수주 추이를 계산한다.

    Args:
        order_entries: 신규수주 항목 리스트
            [{"order_month": "2024-01", "amount": "30000"}, ...]
        prior_year_entries: 전년도 수주 (YoY 비교용)

    Returns:
        (MonthlyNewOrderResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    if not order_entries:
        return MonthlyNewOrderResult(
            months=[],
            amounts={},
            cumulative={},
            yoy_growth={},
            warnings=["ORDERS_EMPTY: No new order data"],
        ), evidence

    # 월별 집계
    monthly: dict[str, Decimal] = {}
    for e in order_entries:
        month = str(e.get(month_key, "")).strip()
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO

        if not month:
            continue
        monthly[month] = monthly.get(month, ZERO) + amount

    months = sorted(monthly.keys())
    amounts = {m: _q(monthly[m]) for m in months}

    # 누적
    cumulative: dict[str, Decimal] = {}
    running = ZERO
    for m in months:
        running += amounts[m]
        cumulative[m] = _q(running)

    # YoY
    yoy: dict[str, Decimal] = {}
    if prior_year_entries:
        prior_monthly: dict[str, Decimal] = {}
        for e in prior_year_entries:
            month = str(e.get(month_key, "")).strip()
            raw = e.get(amount_key, "0")
            amount = _q(abs(Decimal(str(raw)))) if raw else ZERO
            if month:
                prior_monthly[month] = prior_monthly.get(month, ZERO) + amount

        for m in months:
            # 전년 동월 매칭 (YYYY-MM → 이전 해)
            parts = m.split("-")
            if len(parts) == 2:
                prior_m = f"{int(parts[0]) - 1}-{parts[1]}"
                prior_val = prior_monthly.get(prior_m, ZERO)
                if prior_val > ZERO:
                    yoy[m] = _pct((amounts[m] - prior_val) / prior_val * HUNDRED)

    # 경고: 3개월 연속 감소
    if len(months) >= 3:
        for i in range(2, len(months)):
            if amounts[months[i]] < amounts[months[i - 1]] < amounts[months[i - 2]]:
                warnings.append(
                    f"ORDERS_DECLINING: 3+ consecutive months of declining orders "
                    f"({months[i - 2]} to {months[i]})"
                )
                break

    evidence.append(
        EvidenceLinkData(
            target_type="monthly_new_orders",
            source_type="computed",
            source_id="orders:monthly",
            source_detail={
                "months": len(months),
                "total": str(sum(amounts.values())),
                "avg_monthly": str(
                    _q(sum(amounts.values()) / Decimal(str(len(months))))
                ),
            },
        )
    )

    return MonthlyNewOrderResult(
        months=months,
        amounts=amounts,
        cumulative=cumulative,
        yoy_growth=yoy,
        warnings=warnings,
    ), evidence
