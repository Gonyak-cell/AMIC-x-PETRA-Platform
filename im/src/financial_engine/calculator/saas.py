"""Financial Engine -- SaaS 산업별 재무 지표 계산기 (Phase B1).

SaaS/구독 비즈니스 핵심 KPI를 계산합니다:
ARR, MRR, NRR, Gross/Net Churn, LTV, CAC, LTV/CAC, Rule of 40, CAC Payback.

> 마지막 수정: 2026-02-11 15:00:00
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SaaSMetrics:
    """SaaS 산업별 재무 지표 데이터 클래스.

    각 필드는 ``{연도: 값}`` 형태의 딕셔너리입니다.
    계산이 불가능한 연도는 딕셔너리에서 제외됩니다.

    Attributes:
        arr: 연간 반복 매출 (Decimal, 금액)
        mrr: 월간 반복 매출 (Decimal, 금액)
        nrr: 순매출유지율 (%, float)
        gross_churn_rate: 총 이탈률 (%, float)
        net_churn_rate: 순 이탈률 (%, float)
        ltv: 고객 생애 가치 (Decimal, 금액)
        cac: 고객 획득 비용 (Decimal, 금액)
        ltv_cac_ratio: LTV/CAC 비율 (배수, float)
        rule_of_40: Rule of 40 점수 (%, float)
        cac_payback_months: CAC 회수 기간 (개월, float)
    """

    arr: dict[str, Decimal]
    mrr: dict[str, Decimal]
    nrr: dict[str, float]
    gross_churn_rate: dict[str, float]
    net_churn_rate: dict[str, float]
    ltv: dict[str, Decimal]
    cac: dict[str, Decimal]
    ltv_cac_ratio: dict[str, float]
    rule_of_40: dict[str, float]
    cac_payback_months: dict[str, float]


# ---------------------------------------------------------------------------
# 개별 지표 계산 함수
# ---------------------------------------------------------------------------


def calculate_arr(
    subscription_revenue: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """연간 반복 매출(ARR)을 계산합니다.

    연간 구독 매출을 그대로 ARR로 사용합니다.

    Args:
        subscription_revenue: 연도별 구독 매출 ``{연도: Decimal | None}``

    Returns:
        연도별 ARR ``{연도: Decimal}``. None인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_arr({"2023": Decimal("120000")})
        {'2023': Decimal('120000')}
    """
    result: dict[str, Decimal] = {}
    for year, value in subscription_revenue.items():
        if value is not None:
            result[year] = value
    return result


def calculate_mrr(
    subscription_revenue: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """월간 반복 매출(MRR)을 계산합니다.

    MRR = 연간 구독 매출 / 12

    Args:
        subscription_revenue: 연도별 구독 매출 ``{연도: Decimal | None}``

    Returns:
        연도별 MRR ``{연도: Decimal}``. None인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_mrr({"2023": Decimal("120000")})
        {'2023': Decimal('10000')}
    """
    result: dict[str, Decimal] = {}
    for year, value in subscription_revenue.items():
        if value is not None:
            result[year] = value / Decimal("12")
    return result


def calculate_nrr(
    beginning_arr: dict[str, Decimal | None],
    expansion: dict[str, Decimal | None],
    contraction: dict[str, Decimal | None],
    churned: dict[str, Decimal | None],
) -> dict[str, float]:
    """순매출유지율(NRR)을 계산합니다.

    NRR = (기초ARR + 확장 - 축소 - 이탈) / 기초ARR × 100

    Args:
        beginning_arr: 연도별 기초 ARR ``{연도: Decimal | None}``
        expansion: 연도별 확장 매출 ``{연도: Decimal | None}``
        contraction: 연도별 축소 매출 ``{연도: Decimal | None}``
        churned: 연도별 이탈 매출 ``{연도: Decimal | None}``

    Returns:
        연도별 NRR(%) ``{연도: float}``.
        기초ARR이 0 또는 None이거나, 구성요소가 None인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_nrr(
        ...     beginning_arr={"2023": Decimal("100000")},
        ...     expansion={"2023": Decimal("20000")},
        ...     contraction={"2023": Decimal("5000")},
        ...     churned={"2023": Decimal("3000")},
        ... )
        {'2023': 112.0}
    """
    result: dict[str, float] = {}

    for year in beginning_arr:
        b_arr = beginning_arr.get(year)
        exp = expansion.get(year)
        con = contraction.get(year)
        ch = churned.get(year)

        if any(v is None for v in (b_arr, exp, con, ch)):
            logger.debug("NRR 계산 건너뜀 (%s): 입력값 None 포함", year)
            continue

        if b_arr == Decimal("0"):
            logger.debug("NRR 계산 건너뜀 (%s): 기초ARR이 0", year)
            continue

        nrr_val = (b_arr + exp - con - ch) / b_arr * Decimal("100")  # type: ignore[operator]
        result[year] = float(nrr_val)

    return result


def calculate_gross_churn(
    churned_revenue: dict[str, Decimal | None],
    contraction_revenue: dict[str, Decimal | None],
    beginning_arr: dict[str, Decimal | None],
) -> dict[str, float]:
    """총 이탈률(Gross Churn Rate)을 계산합니다.

    Gross Churn = (이탈 + 축소) / 기초ARR × 100

    Args:
        churned_revenue: 연도별 이탈 매출 ``{연도: Decimal | None}``
        contraction_revenue: 연도별 축소 매출 ``{연도: Decimal | None}``
        beginning_arr: 연도별 기초 ARR ``{연도: Decimal | None}``

    Returns:
        연도별 Gross Churn(%) ``{연도: float}``.
        기초ARR이 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in beginning_arr:
        b_arr = beginning_arr.get(year)
        ch = churned_revenue.get(year)
        con = contraction_revenue.get(year)

        if any(v is None for v in (b_arr, ch, con)):
            continue

        if b_arr == Decimal("0"):
            continue

        churn_val = (ch + con) / b_arr * Decimal("100")  # type: ignore[operator]
        result[year] = float(churn_val)

    return result


def calculate_net_churn(
    churned_revenue: dict[str, Decimal | None],
    contraction_revenue: dict[str, Decimal | None],
    expansion_revenue: dict[str, Decimal | None],
    beginning_arr: dict[str, Decimal | None],
) -> dict[str, float]:
    """순 이탈률(Net Churn Rate)을 계산합니다.

    Net Churn = (이탈 + 축소 - 확장) / 기초ARR × 100.
    음수 가능 (확장이 이탈+축소보다 클 때 = net expansion).

    Args:
        churned_revenue: 연도별 이탈 매출 ``{연도: Decimal | None}``
        contraction_revenue: 연도별 축소 매출 ``{연도: Decimal | None}``
        expansion_revenue: 연도별 확장 매출 ``{연도: Decimal | None}``
        beginning_arr: 연도별 기초 ARR ``{연도: Decimal | None}``

    Returns:
        연도별 Net Churn(%) ``{연도: float}``. 음수 허용.
    """
    result: dict[str, float] = {}

    for year in beginning_arr:
        b_arr = beginning_arr.get(year)
        ch = churned_revenue.get(year)
        con = contraction_revenue.get(year)
        exp = expansion_revenue.get(year)

        if any(v is None for v in (b_arr, ch, con, exp)):
            continue

        if b_arr == Decimal("0"):
            continue

        net_churn_val = (ch + con - exp) / b_arr * Decimal("100")  # type: ignore[operator]
        result[year] = float(net_churn_val)

    return result


def calculate_ltv(
    arpu: dict[str, Decimal | None],
    gross_margin_pct: dict[str, Decimal | None],
    churn_rate: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """고객 생애 가치(LTV)를 계산합니다.

    LTV = ARPU × 매출총이익률 / 연간 Churn Rate

    Args:
        arpu: 연도별 고객당 평균 매출 ``{연도: Decimal | None}``
        gross_margin_pct: 연도별 매출총이익률 (소수, 예: 0.80 = 80%)
        churn_rate: 연도별 연간 이탈률 (소수, 예: 0.05 = 5%)

    Returns:
        연도별 LTV ``{연도: Decimal}``.
        Churn Rate가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, Decimal] = {}

    for year in arpu:
        a = arpu.get(year)
        gm = gross_margin_pct.get(year)
        cr = churn_rate.get(year)

        if any(v is None for v in (a, gm, cr)):
            continue

        if cr == Decimal("0"):
            logger.debug("LTV 계산 건너뜀 (%s): Churn Rate가 0", year)
            continue

        result[year] = a * gm / cr  # type: ignore[operator]

    return result


def calculate_cac(
    sales_marketing_cost: dict[str, Decimal | None],
    new_customers: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """고객 획득 비용(CAC)을 계산합니다.

    CAC = 영업·마케팅비 / 신규 고객 수

    Args:
        sales_marketing_cost: 연도별 영업·마케팅 비용 ``{연도: Decimal | None}``
        new_customers: 연도별 신규 고객 수 ``{연도: Decimal | None}``

    Returns:
        연도별 CAC ``{연도: Decimal}``.
        신규 고객 수가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, Decimal] = {}

    for year in sales_marketing_cost:
        cost = sales_marketing_cost.get(year)
        nc = new_customers.get(year)

        if cost is None or nc is None:
            continue

        if nc == Decimal("0"):
            logger.debug("CAC 계산 건너뜀 (%s): 신규 고객 수가 0", year)
            continue

        result[year] = cost / nc

    return result


def calculate_ltv_cac_ratio(
    ltv: dict[str, Decimal],
    cac: dict[str, Decimal],
) -> dict[str, float]:
    """LTV/CAC 비율을 계산합니다.

    Args:
        ltv: 연도별 LTV ``{연도: Decimal}``
        cac: 연도별 CAC ``{연도: Decimal}``

    Returns:
        연도별 LTV/CAC 배수 ``{연도: float}``.
        CAC가 0이거나 양쪽에 공통 연도가 없으면 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_ltv_cac_ratio(
        ...     ltv={"2023": Decimal("15000")},
        ...     cac={"2023": Decimal("5000")},
        ... )
        {'2023': 3.0}
    """
    result: dict[str, float] = {}

    for year in ltv:
        ltv_val = ltv.get(year)
        cac_val = cac.get(year)

        if ltv_val is None or cac_val is None:
            continue

        if cac_val == Decimal("0"):
            logger.debug("LTV/CAC 계산 건너뜀 (%s): CAC가 0", year)
            continue

        result[year] = float(ltv_val / cac_val)

    return result


def calculate_rule_of_40(
    revenue_growth_rate: dict[str, float],
    operating_margin: dict[str, float],
) -> dict[str, float]:
    """Rule of 40 점수를 계산합니다.

    Rule of 40 = 매출 성장률(%) + 영업이익률(%)

    Args:
        revenue_growth_rate: 연도별 매출 YoY 성장률 (%) ``{연도: float}``
        operating_margin: 연도별 영업이익률 (%) ``{연도: float}``

    Returns:
        연도별 Rule of 40 점수(%) ``{연도: float}``.
        양쪽 모두 존재하는 연도만 계산됩니다.

    Examples:
        >>> calculate_rule_of_40(
        ...     revenue_growth_rate={"2023": 30.0},
        ...     operating_margin={"2023": 15.0},
        ... )
        {'2023': 45.0}
    """
    result: dict[str, float] = {}

    for year in revenue_growth_rate:
        growth = revenue_growth_rate.get(year)
        margin = operating_margin.get(year)

        if growth is None or margin is None:
            continue

        result[year] = growth + margin

    return result


def calculate_cac_payback(
    cac: dict[str, Decimal],
    mrr_per_customer: dict[str, Decimal | None],
    gross_margin_pct: dict[str, Decimal | None],
) -> dict[str, float]:
    """CAC 회수 기간을 계산합니다 (개월).

    CAC Payback = CAC / (고객당 MRR × 매출총이익률)

    Args:
        cac: 연도별 CAC ``{연도: Decimal}``
        mrr_per_customer: 연도별 고객당 MRR ``{연도: Decimal | None}``
        gross_margin_pct: 연도별 매출총이익률 (소수) ``{연도: Decimal | None}``

    Returns:
        연도별 CAC 회수 기간(개월) ``{연도: float}``.
        분모(MRR × 총이익률)가 0인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in cac:
        cac_val = cac.get(year)
        mrr = mrr_per_customer.get(year)
        gm = gross_margin_pct.get(year)

        if any(v is None for v in (cac_val, mrr, gm)):
            continue

        denominator = mrr * gm  # type: ignore[operator]
        if denominator == Decimal("0"):
            logger.debug("CAC Payback 계산 건너뜀 (%s): 분모가 0", year)
            continue

        result[year] = float(cac_val / denominator)  # type: ignore[operator]

    return result


# ---------------------------------------------------------------------------
# 통합 계산 함수
# ---------------------------------------------------------------------------


def calculate_saas_metrics(
    revenue: dict[str, Decimal | None],
    subscription_revenue: dict[str, Decimal | None],
    beginning_arr: dict[str, Decimal | None] | None = None,
    expansion_revenue: dict[str, Decimal | None] | None = None,
    contraction_revenue: dict[str, Decimal | None] | None = None,
    churned_revenue: dict[str, Decimal | None] | None = None,
    sales_marketing_cost: dict[str, Decimal | None] | None = None,
    new_customers: dict[str, Decimal | None] | None = None,
    arpu: dict[str, Decimal | None] | None = None,
    gross_margin_pct: dict[str, Decimal | None] | None = None,
    revenue_growth_rate: dict[str, float] | None = None,
    operating_margin: dict[str, float] | None = None,
) -> SaaSMetrics:
    """SaaS 산업별 재무 지표를 일괄 계산합니다.

    ``revenue``와 ``subscription_revenue``는 필수이며, 나머지 입력은 선택입니다.
    선택 입력이 제공되지 않으면 해당 지표는 빈 딕셔너리로 반환됩니다.

    Args:
        revenue: 연도별 매출액 ``{연도: Decimal | None}``
        subscription_revenue: 연도별 구독 매출 ``{연도: Decimal | None}``
        beginning_arr: 연도별 기초 ARR (선택)
        expansion_revenue: 연도별 확장 매출 (선택)
        contraction_revenue: 연도별 축소 매출 (선택)
        churned_revenue: 연도별 이탈 매출 (선택)
        sales_marketing_cost: 연도별 영업·마케팅 비용 (선택)
        new_customers: 연도별 신규 고객 수 (선택)
        arpu: 연도별 고객당 평균 매출 (선택)
        gross_margin_pct: 연도별 매출총이익률, 소수 (선택)
        revenue_growth_rate: 연도별 매출 YoY 성장률 % (선택)
        operating_margin: 연도별 영업이익률 % (선택)

    Returns:
        SaaSMetrics: 계산된 SaaS 지표 데이터 클래스.
    """
    # 1) ARR & MRR (필수)
    arr = calculate_arr(subscription_revenue)
    mrr = calculate_mrr(subscription_revenue)

    # 2) NRR (선택)
    nrr: dict[str, float] = {}
    if all(
        v is not None
        for v in (
            beginning_arr,
            expansion_revenue,
            contraction_revenue,
            churned_revenue,
        )
    ):
        nrr = calculate_nrr(
            beginning_arr,
            expansion_revenue,
            contraction_revenue,
            churned_revenue,  # type: ignore[arg-type]
        )

    # 3) Gross Churn (선택)
    gross_churn: dict[str, float] = {}
    if all(
        v is not None for v in (churned_revenue, contraction_revenue, beginning_arr)
    ):
        gross_churn = calculate_gross_churn(
            churned_revenue,
            contraction_revenue,
            beginning_arr,  # type: ignore[arg-type]
        )

    # 4) Net Churn (선택)
    net_churn: dict[str, float] = {}
    if all(
        v is not None
        for v in (
            churned_revenue,
            contraction_revenue,
            expansion_revenue,
            beginning_arr,
        )
    ):
        net_churn = calculate_net_churn(
            churned_revenue,
            contraction_revenue,
            expansion_revenue,
            beginning_arr,  # type: ignore[arg-type]
        )

    # 5) LTV (선택)
    ltv: dict[str, Decimal] = {}
    churn_rate_for_ltv: dict[str, Decimal | None] | None = None
    if beginning_arr is not None and churned_revenue is not None:
        # 연간 churn rate = churned / beginning_arr (소수)
        churn_rate_for_ltv = {}
        for year in beginning_arr:
            b = beginning_arr.get(year)
            c = churned_revenue.get(year)
            if b is not None and c is not None and b != Decimal("0"):
                churn_rate_for_ltv[year] = c / b
            else:
                churn_rate_for_ltv[year] = None

    if all(v is not None for v in (arpu, gross_margin_pct, churn_rate_for_ltv)):
        ltv = calculate_ltv(arpu, gross_margin_pct, churn_rate_for_ltv)  # type: ignore[arg-type]

    # 6) CAC (선택)
    cac: dict[str, Decimal] = {}
    if sales_marketing_cost is not None and new_customers is not None:
        cac = calculate_cac(sales_marketing_cost, new_customers)

    # 7) LTV/CAC (선택 -- LTV와 CAC 모두 필요)
    ltv_cac: dict[str, float] = {}
    if ltv and cac:
        ltv_cac = calculate_ltv_cac_ratio(ltv, cac)

    # 8) Rule of 40 (선택)
    rule_40: dict[str, float] = {}
    if revenue_growth_rate is not None and operating_margin is not None:
        rule_40 = calculate_rule_of_40(revenue_growth_rate, operating_margin)

    # 9) CAC Payback (선택 -- CAC, MRR per customer, gross margin 필요)
    cac_payback: dict[str, float] = {}
    if cac and arpu is not None and gross_margin_pct is not None:
        # MRR per customer = ARPU / 12
        mrr_per_cust: dict[str, Decimal | None] = {}
        for year, a in arpu.items():
            if a is not None:
                mrr_per_cust[year] = a / Decimal("12")
            else:
                mrr_per_cust[year] = None
        cac_payback = calculate_cac_payback(cac, mrr_per_cust, gross_margin_pct)

    return SaaSMetrics(
        arr=arr,
        mrr=mrr,
        nrr=nrr,
        gross_churn_rate=gross_churn,
        net_churn_rate=net_churn,
        ltv=ltv,
        cac=cac,
        ltv_cac_ratio=ltv_cac,
        rule_of_40=rule_40,
        cac_payback_months=cac_payback,
    )
