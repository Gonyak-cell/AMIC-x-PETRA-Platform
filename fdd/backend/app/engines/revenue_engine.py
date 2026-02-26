"""매출 Deep-dive 엔진 — 거래처/제품/사업부/월별/지역별 분석.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.

Big 4 WP 수준의 매출 다차원 분석을 지원:
- 차원별 Breakdown (거래처/제품/사업부/월별/지역별)
- HHI 집중도 지수 (0~10,000)
- Top N 매출 비중
- 기간별 YoY 변동
- 월별 추이 (계절성 패턴 감지)
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
TEN_THOUSAND = Decimal("10000")


def _q(amount: Decimal) -> Decimal:
    """NUMERIC(18,4) 정밀도로 반올림."""
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


def _pct(value: Decimal) -> Decimal:
    """퍼센트 정밀도 (소수점 2자리)."""
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class EvidenceLinkData:
    """Evidence link data (엔진 → 서비스 출력용)."""

    target_type: str
    source_type: str
    source_id: str
    source_detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class RevenueItem:
    """매출 분해 항목."""

    name: str                               # 거래처명/제품명/사업부명/월
    amounts_by_period: dict[str, Decimal]    # {"FY2023": Decimal("50000"), ...}
    total: Decimal                           # 전체 기간 합계 (또는 최신 기간)
    share_pct: Decimal                       # 비중 (%)
    yoy_pct: Decimal | None                  # YoY 변동률 (%), None if insufficient
    rank: int                                # 순위 (1-based)


@dataclass(frozen=True)
class MonthlyTrendItem:
    """월별 추이 항목."""

    month: str                              # "2024-01", "2024-02", ...
    amount: Decimal
    yoy_pct: Decimal | None                 # 전년 동월 대비 %


@dataclass
class RevenueBreakdownResult:
    """매출 분해 분석 결과."""

    dimension: str                          # "customer" | "product" | "segment" | "month" | "region"
    period_labels: list[str]                # 분석 대상 기간 레이블
    breakdown: list[RevenueItem]            # 항목별 결과 (rank 순)
    total_revenue: Decimal                  # 전체 매출 합계
    concentration_index: Decimal            # HHI (0~10,000)
    top_n_share: Decimal                    # Top 5 매출 비중 (%)
    top_n_count: int                        # Top N 기준 (기본 5)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MonthlyTrendResult:
    """월별 매출 추이 결과."""

    months: list[str]                       # ["2024-01", "2024-02", ...]
    trend: list[MonthlyTrendItem]           # 월별 데이터
    total: Decimal                          # 전체 합계
    average_monthly: Decimal                # 월평균
    seasonality_index: dict[str, Decimal]   # 월별 계절성 지수 (평균=100)
    peak_month: str                         # 최고 매출 월
    trough_month: str                       # 최저 매출 월
    warnings: list[str] = field(default_factory=list)


# ── Core: Revenue Breakdown ───────────────────────────────


def compute_revenue_breakdown(
    entries: list[dict[str, Any]],
    *,
    dimension: str,
    dimension_key: str,
    periods: list[str] | None = None,
    period_key: str = "period",
    amount_key: str = "amount",
    top_n: int = 5,
    others_label: str = "기타 (Others)",
) -> tuple[RevenueBreakdownResult, list[EvidenceLinkData]]:
    """매출을 차원별로 분해 분석한다.

    Args:
        entries: GL/매출 데이터 (dict 리스트)
            각 dict에는 dimension_key, period_key, amount_key가 포함.
            예: [{"customer": "A사", "period": "FY2023", "amount": "50000"}, ...]
        dimension: 분석 차원 ("customer"|"product"|"segment"|"month"|"region")
        dimension_key: 차원 값 필드명 (예: "customer_name")
        periods: 분석 대상 기간 (None이면 entries에서 자동 추출)
        period_key: 기간 필드명
        amount_key: 금액 필드명
        top_n: Top N 계산 기준 (기본 5)
        others_label: Top N 이외를 합산할 라벨

    Returns:
        (RevenueBreakdownResult, evidence_links)
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    # 기간 레이블 추출
    all_periods: set[str] = set()
    for e in entries:
        p = str(e.get(period_key, ""))
        if p:
            all_periods.add(p)
    period_labels = sorted(periods or list(all_periods))

    # 차원별 × 기간별 금액 집계
    dim_period_amounts: dict[str, dict[str, Decimal]] = {}
    for e in entries:
        dim_val = str(e.get(dimension_key, "")).strip()
        period = str(e.get(period_key, "")).strip()
        raw_amount = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw_amount)))) if raw_amount else ZERO

        if not dim_val or not period:
            continue

        dim_period_amounts.setdefault(dim_val, {})
        dim_period_amounts[dim_val][period] = (
            dim_period_amounts[dim_val].get(period, ZERO) + amount
        )

    if not dim_period_amounts:
        warnings.append(f"REVENUE_EMPTY: No data for dimension '{dimension}'")
        return (
            RevenueBreakdownResult(
                dimension=dimension,
                period_labels=period_labels,
                breakdown=[],
                total_revenue=ZERO,
                concentration_index=ZERO,
                top_n_share=ZERO,
                top_n_count=top_n,
                warnings=warnings,
            ),
            evidence,
        )

    # 총 매출 계산 (최신 기간 기준 또는 전체 합산)
    latest_period = period_labels[-1] if period_labels else None

    # 각 차원 항목의 총액 (최신 기간 기준)
    dim_totals: dict[str, Decimal] = {}
    for dim_val, period_amounts in dim_period_amounts.items():
        if latest_period and latest_period in period_amounts:
            dim_totals[dim_val] = period_amounts[latest_period]
        else:
            # 전 기간 합산
            dim_totals[dim_val] = sum(period_amounts.values(), ZERO)

    # 총 매출
    total_revenue = _q(sum(dim_totals.values(), ZERO))

    if total_revenue == ZERO:
        warnings.append("REVENUE_ZERO: Total revenue is zero")
        return (
            RevenueBreakdownResult(
                dimension=dimension,
                period_labels=period_labels,
                breakdown=[],
                total_revenue=ZERO,
                concentration_index=ZERO,
                top_n_share=ZERO,
                top_n_count=top_n,
                warnings=warnings,
            ),
            evidence,
        )

    # 순위 정렬 (금액 내림차순)
    sorted_dims = sorted(dim_totals.items(), key=lambda x: x[1], reverse=True)

    # Top N + Others 구분
    top_items = sorted_dims[:top_n]
    others_items = sorted_dims[top_n:]

    # RevenueItem 생성
    breakdown: list[RevenueItem] = []
    rank = 1

    for dim_val, total in top_items:
        period_amounts = dim_period_amounts[dim_val]

        # YoY 계산 (최근 2 FY 기간)
        yoy = _compute_dim_yoy(period_amounts, period_labels)

        # 비중 계산
        share = _pct(total / total_revenue * HUNDRED)

        breakdown.append(
            RevenueItem(
                name=dim_val,
                amounts_by_period=period_amounts,
                total=_q(total),
                share_pct=share,
                yoy_pct=yoy,
                rank=rank,
            )
        )

        # Evidence
        evidence.append(
            EvidenceLinkData(
                target_type=f"revenue_{dimension}",
                source_type="GL",
                source_id=f"{dimension}:{dim_val}",
                source_detail={
                    "dimension": dimension,
                    "value": dim_val,
                    "total": str(total),
                    "share_pct": str(share),
                },
            )
        )

        rank += 1

    # Others 합산
    if others_items:
        others_period_amounts: dict[str, Decimal] = {}
        others_total = ZERO
        for dim_val, total in others_items:
            others_total += total
            for p, amt in dim_period_amounts[dim_val].items():
                others_period_amounts[p] = others_period_amounts.get(p, ZERO) + amt

        others_share = _pct(others_total / total_revenue * HUNDRED)
        others_yoy = _compute_dim_yoy(others_period_amounts, period_labels)

        breakdown.append(
            RevenueItem(
                name=others_label,
                amounts_by_period=others_period_amounts,
                total=_q(others_total),
                share_pct=others_share,
                yoy_pct=others_yoy,
                rank=rank,
            )
        )

    # HHI 집중도 지수
    hhi = _compute_hhi(dim_totals, total_revenue)

    # Top N 비중
    top_n_total = sum(t for _, t in top_items)
    top_n_share = _pct(top_n_total / total_revenue * HUNDRED)

    # 경고 생성
    if hhi > Decimal("2500"):
        warnings.append(
            f"REVENUE_HIGH_CONCENTRATION: HHI={hhi} (>2500) — "
            "매출 집중도가 높습니다"
        )

    if top_n_share > Decimal("80"):
        warnings.append(
            f"REVENUE_TOP_N_DOMINANT: Top {top_n} = {top_n_share}% — "
            "소수 거래처/제품에 매출이 집중되어 있습니다"
        )

    result = RevenueBreakdownResult(
        dimension=dimension,
        period_labels=period_labels,
        breakdown=breakdown,
        total_revenue=total_revenue,
        concentration_index=hhi,
        top_n_share=top_n_share,
        top_n_count=top_n,
        warnings=warnings,
        metadata={
            "engine_version": ENGINE_VERSION,
            "unique_items": len(dim_totals),
            "top_n": top_n,
        },
    )

    return result, evidence


# ── Core: Monthly Trend ───────────────────────────────────


def compute_monthly_trend(
    entries: list[dict[str, Any]],
    *,
    month_key: str = "month",
    amount_key: str = "amount",
    prior_year_entries: list[dict[str, Any]] | None = None,
) -> tuple[MonthlyTrendResult, list[EvidenceLinkData]]:
    """월별 매출 추이를 분석한다.

    Args:
        entries: 월별 매출 데이터
            예: [{"month": "2024-01", "amount": "50000"}, ...]
        month_key: 월 필드명
        amount_key: 금액 필드명
        prior_year_entries: 전년 동기 데이터 (YoY 비교용)

    Returns:
        (MonthlyTrendResult, evidence_links)
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    # 월별 집계
    monthly_amounts: dict[str, Decimal] = {}
    for e in entries:
        month = str(e.get(month_key, "")).strip()
        raw_amount = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw_amount)))) if raw_amount else ZERO
        if month:
            monthly_amounts[month] = monthly_amounts.get(month, ZERO) + amount

    # 전년 동기 집계
    prior_amounts: dict[str, Decimal] = {}
    if prior_year_entries:
        for e in prior_year_entries:
            month = str(e.get(month_key, "")).strip()
            raw_amount = e.get(amount_key, "0")
            amount = _q(abs(Decimal(str(raw_amount)))) if raw_amount else ZERO
            if month:
                prior_amounts[month] = prior_amounts.get(month, ZERO) + amount

    # 정렬
    sorted_months = sorted(monthly_amounts.keys())

    if not sorted_months:
        warnings.append("MONTHLY_EMPTY: No monthly data")
        return (
            MonthlyTrendResult(
                months=[],
                trend=[],
                total=ZERO,
                average_monthly=ZERO,
                seasonality_index={},
                peak_month="",
                trough_month="",
                warnings=warnings,
            ),
            evidence,
        )

    # 총계/평균
    total = _q(sum(monthly_amounts.values(), ZERO))
    count = Decimal(str(len(sorted_months)))
    average = _q(total / count) if count > ZERO else ZERO

    # 추이 데이터 생성
    trend: list[MonthlyTrendItem] = []
    for month in sorted_months:
        amount = monthly_amounts[month]

        # YoY: 전년 동월 비교 (month format: "2024-01" → prior: "2023-01")
        yoy = None
        if prior_amounts:
            prior_month = _prior_year_month(month)
            prior_val = prior_amounts.get(prior_month, ZERO)
            if prior_val > ZERO:
                yoy = _pct((amount - prior_val) / prior_val * HUNDRED)

        trend.append(
            MonthlyTrendItem(month=month, amount=amount, yoy_pct=yoy)
        )

        evidence.append(
            EvidenceLinkData(
                target_type="revenue_monthly",
                source_type="GL",
                source_id=f"month:{month}",
                source_detail={"month": month, "amount": str(amount)},
            )
        )

    # 계절성 지수 (월평균 = 100 기준)
    seasonality: dict[str, Decimal] = {}
    if average > ZERO:
        for month in sorted_months:
            idx = _pct(monthly_amounts[month] / average * HUNDRED)
            seasonality[month] = idx

    # 최고/최저 월
    peak_month = max(sorted_months, key=lambda m: monthly_amounts[m])
    trough_month = min(sorted_months, key=lambda m: monthly_amounts[m])

    # 경고
    if seasonality:
        max_idx = max(seasonality.values())
        min_idx = min(seasonality.values())
        spread = max_idx - min_idx
        if spread > Decimal("100"):
            warnings.append(
                f"SEASONALITY_HIGH: 계절성 편차 {spread}pt — "
                "뚜렷한 계절적 패턴이 존재합니다"
            )

    result = MonthlyTrendResult(
        months=sorted_months,
        trend=trend,
        total=total,
        average_monthly=average,
        seasonality_index=seasonality,
        peak_month=peak_month,
        trough_month=trough_month,
        warnings=warnings,
    )

    return result, evidence


# ── Helpers ───────────────────────────────────────────────


def _compute_hhi(
    dim_totals: dict[str, Decimal],
    total_revenue: Decimal,
) -> Decimal:
    """HHI (Herfindahl-Hirschman Index)를 계산한다.

    HHI = Σ(s_i^2) where s_i = market share (0~100)
    범위: 0 (완전 분산) ~ 10,000 (독점)
    - < 1,500: 비집중
    - 1,500 ~ 2,500: 중간 집중
    - > 2,500: 고집중
    """
    if total_revenue == ZERO:
        return ZERO

    hhi = ZERO
    for _, amount in dim_totals.items():
        share = amount / total_revenue * HUNDRED  # 0~100%
        hhi += share * share  # s_i^2

    return _pct(hhi)


def _compute_dim_yoy(
    period_amounts: dict[str, Decimal],
    period_labels: list[str],
) -> Decimal | None:
    """최근 2개 FY 기간 간 YoY 변동률 (%)."""
    fy_labels = [l for l in period_labels if l.startswith("FY")]
    if len(fy_labels) < 2:
        return None

    prev_label = fy_labels[-2]
    curr_label = fy_labels[-1]
    prev_val = period_amounts.get(prev_label, ZERO)
    curr_val = period_amounts.get(curr_label, ZERO)

    if prev_val == ZERO:
        return None

    return _pct((curr_val - prev_val) / prev_val * HUNDRED)


def _prior_year_month(month: str) -> str:
    """월 레이블에서 전년 동월을 계산한다.

    "2024-01" → "2023-01"
    """
    parts = month.split("-")
    if len(parts) == 2:
        try:
            year = int(parts[0])
            return f"{year - 1}-{parts[1]}"
        except ValueError:
            pass
    return ""
