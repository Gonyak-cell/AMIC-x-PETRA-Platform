"""Financial Engine -- Cash Flow Calculator (T-F08).

현금흐름 지표를 계산합니다: EBITDA, FCF, NWC, EBITDA Margin.

EBITDA = 영업이익 + 감가상각비 + 무형자산상각비
FCF    = 영업활동 현금흐름 - 자본적 지출 (CapEx)
NWC    = 유동자산 - 유동부채

> 마지막 수정: 2026-02-09 16:08:43
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CashFlowMetrics:
    """현금흐름 지표 데이터 클래스.

    각 필드는 ``{연도: 값}`` 형태의 딕셔너리입니다.
    계산이 불가능한 연도(필수 입력값이 ``None``)는 딕셔너리에서 제외됩니다.

    Attributes:
        ebitda: 연도별 EBITDA (Decimal)
        free_cash_flow: 연도별 잉여현금흐름 (Decimal)
        net_working_capital: 연도별 순운전자본 (Decimal)
        ebitda_margin: 연도별 EBITDA 마진 (%, float)
    """

    ebitda: dict[str, Decimal]
    free_cash_flow: dict[str, Decimal]
    net_working_capital: dict[str, Decimal]
    ebitda_margin: dict[str, float]


# ---------------------------------------------------------------------------
# 개별 지표 계산 함수
# ---------------------------------------------------------------------------


def calculate_ebitda(
    operating_income: dict[str, Decimal | None],
    depreciation: dict[str, Decimal | None],
    amortization: dict[str, Decimal | None] | None = None,
) -> dict[str, Decimal]:
    """EBITDA를 연도별로 계산합니다.

    EBITDA = 영업이익(Operating Income) + 감가상각비(Depreciation)
             + 무형자산상각비(Amortization, 있는 경우)

    감가상각비(``depreciation``)가 ``None``인 연도는 EBITDA를 산출할 수 없으므로
    결과에서 제외됩니다. ``amortization`` 딕셔너리 자체가 ``None``이면
    상각비 없이 영업이익 + 감가상각비만으로 계산합니다. 단, ``amortization``
    딕셔너리가 제공되었으나 해당 연도의 값이 ``None``인 경우에는
    해당 연도를 건너뜁니다.

    Args:
        operating_income: 연도별 영업이익 ``{연도: Decimal | None}``
        depreciation: 연도별 감가상각비 ``{연도: Decimal | None}``
        amortization: 연도별 무형자산상각비 ``{연도: Decimal | None}`` (선택).
            딕셔너리 자체가 ``None``이면 상각비 없이 계산합니다.

    Returns:
        연도별 EBITDA 딕셔너리 ``{연도: Decimal}``.
        필수 입력값이 ``None``인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> oi = {"2022": Decimal("500"), "2023": Decimal("600")}
        >>> dep = {"2022": Decimal("100"), "2023": Decimal("120")}
        >>> calculate_ebitda(oi, dep)
        {'2022': Decimal('600'), '2023': Decimal('720')}
        >>> amort = {"2022": Decimal("50"), "2023": None}
        >>> calculate_ebitda(oi, dep, amort)
        {'2022': Decimal('650')}
    """
    result: dict[str, Decimal] = {}

    for year in operating_income:
        oi = operating_income.get(year)
        dep = depreciation.get(year)

        # 영업이익 또는 감가상각비가 None이면 건너뜀
        if oi is None or dep is None:
            logger.debug("EBITDA 계산 건너뜀 (%s): 영업이익=%s, 감가상각비=%s", year, oi, dep)
            continue

        ebitda = oi + dep

        # amortization 딕셔너리가 제공된 경우 해당 연도 값 확인
        if amortization is not None:
            amort_val = amortization.get(year)
            if amort_val is None:
                logger.debug(
                    "EBITDA 계산 건너뜀 (%s): 무형자산상각비가 None", year
                )
                continue
            ebitda += amort_val

        result[year] = ebitda

    return result


def calculate_fcf(
    operating_cash_flow: dict[str, Decimal | None],
    capex: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """잉여현금흐름(FCF)을 연도별로 계산합니다.

    FCF = 영업활동 현금흐름(Operating Cash Flow) - |CapEx|

    CapEx는 현금흐름표에서 통상 음수로 보고되므로, 절대값을 취하여 차감합니다.
    필수 입력값이 ``None``인 연도는 결과에서 제외됩니다.

    Args:
        operating_cash_flow: 연도별 영업활동 현금흐름 ``{연도: Decimal | None}``
        capex: 연도별 자본적 지출 ``{연도: Decimal | None}``.
            음수 또는 양수 모두 허용되며, 내부적으로 절대값을 사용합니다.

    Returns:
        연도별 FCF 딕셔너리 ``{연도: Decimal}``.
        필수 입력값이 ``None``인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> ocf = {"2022": Decimal("800"), "2023": Decimal("900")}
        >>> capex = {"2022": Decimal("-200"), "2023": Decimal("250")}
        >>> calculate_fcf(ocf, capex)
        {'2022': Decimal('600'), '2023': Decimal('650')}
    """
    result: dict[str, Decimal] = {}

    for year in operating_cash_flow:
        ocf = operating_cash_flow.get(year)
        cx = capex.get(year)

        if ocf is None or cx is None:
            logger.debug(
                "FCF 계산 건너뜀 (%s): 영업활동CF=%s, CapEx=%s", year, ocf, cx
            )
            continue

        result[year] = ocf - abs(cx)

    return result


def calculate_nwc(
    current_assets: dict[str, Decimal | None],
    current_liabilities: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """순운전자본(NWC)을 연도별로 계산합니다.

    NWC = 유동자산(Current Assets) - 유동부채(Current Liabilities)

    필수 입력값이 ``None``인 연도는 결과에서 제외됩니다.

    Args:
        current_assets: 연도별 유동자산 ``{연도: Decimal | None}``
        current_liabilities: 연도별 유동부채 ``{연도: Decimal | None}``

    Returns:
        연도별 NWC 딕셔너리 ``{연도: Decimal}``.
        필수 입력값이 ``None``인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> ca = {"2022": Decimal("3000"), "2023": Decimal("3500")}
        >>> cl = {"2022": Decimal("1500"), "2023": Decimal("1800")}
        >>> calculate_nwc(ca, cl)
        {'2022': Decimal('1500'), '2023': Decimal('1700')}
    """
    result: dict[str, Decimal] = {}

    for year in current_assets:
        ca = current_assets.get(year)
        cl = current_liabilities.get(year)

        if ca is None or cl is None:
            logger.debug(
                "NWC 계산 건너뜀 (%s): 유동자산=%s, 유동부채=%s", year, ca, cl
            )
            continue

        result[year] = ca - cl

    return result


# ---------------------------------------------------------------------------
# 통합 계산 함수
# ---------------------------------------------------------------------------


def calculate_cash_flow_metrics(
    operating_income: dict[str, Decimal | None],
    depreciation: dict[str, Decimal | None],
    amortization: dict[str, Decimal | None] | None = None,
    operating_cash_flow: dict[str, Decimal | None] | None = None,
    capex: dict[str, Decimal | None] | None = None,
    current_assets: dict[str, Decimal | None] | None = None,
    current_liabilities: dict[str, Decimal | None] | None = None,
    revenue: dict[str, Decimal | None] | None = None,
) -> CashFlowMetrics:
    """현금흐름 관련 지표를 일괄 계산합니다.

    EBITDA는 ``operating_income``과 ``depreciation``이 필수이므로 항상 계산됩니다.
    FCF, NWC, EBITDA Margin은 해당 입력 딕셔너리가 제공된 경우에만 계산되며,
    제공되지 않으면 빈 딕셔너리로 반환됩니다.

    EBITDA Margin = EBITDA / Revenue * 100 (%)

    Args:
        operating_income: 연도별 영업이익 ``{연도: Decimal | None}``
        depreciation: 연도별 감가상각비 ``{연도: Decimal | None}``
        amortization: 연도별 무형자산상각비 ``{연도: Decimal | None}`` (선택)
        operating_cash_flow: 연도별 영업활동 현금흐름 (선택)
        capex: 연도별 자본적 지출 (선택)
        current_assets: 연도별 유동자산 (선택)
        current_liabilities: 연도별 유동부채 (선택)
        revenue: 연도별 매출액 (선택). EBITDA Margin 계산에 사용됩니다.

    Returns:
        CashFlowMetrics: 계산된 현금흐름 지표 데이터 클래스.
            - ebitda: 항상 계산
            - free_cash_flow: ``operating_cash_flow``와 ``capex``가 모두 제공된 경우 계산
            - net_working_capital: ``current_assets``와 ``current_liabilities``가 모두 제공된 경우 계산
            - ebitda_margin: ``revenue``가 제공된 경우 계산

    Examples:
        >>> from decimal import Decimal
        >>> result = calculate_cash_flow_metrics(
        ...     operating_income={"2023": Decimal("600")},
        ...     depreciation={"2023": Decimal("120")},
        ...     revenue={"2023": Decimal("2000")},
        ... )
        >>> result.ebitda
        {'2023': Decimal('720')}
        >>> result.ebitda_margin
        {'2023': 36.0}
    """
    # 1) EBITDA (필수)
    ebitda = calculate_ebitda(operating_income, depreciation, amortization)

    # 2) FCF (선택)
    fcf: dict[str, Decimal] = {}
    if operating_cash_flow is not None and capex is not None:
        fcf = calculate_fcf(operating_cash_flow, capex)

    # 3) NWC (선택)
    nwc: dict[str, Decimal] = {}
    if current_assets is not None and current_liabilities is not None:
        nwc = calculate_nwc(current_assets, current_liabilities)

    # 4) EBITDA Margin (선택 -- revenue 필요)
    ebitda_margin: dict[str, float] = {}
    if revenue is not None:
        ebitda_margin = _calculate_ebitda_margin(ebitda, revenue)

    return CashFlowMetrics(
        ebitda=ebitda,
        free_cash_flow=fcf,
        net_working_capital=nwc,
        ebitda_margin=ebitda_margin,
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼 함수
# ---------------------------------------------------------------------------


def _calculate_ebitda_margin(
    ebitda: dict[str, Decimal],
    revenue: dict[str, Decimal | None],
) -> dict[str, float]:
    """EBITDA 마진을 연도별로 계산합니다.

    EBITDA Margin = EBITDA / Revenue * 100 (%)

    EBITDA가 계산된 연도 중 매출액이 ``None``이거나 0인 연도는 제외됩니다.

    Args:
        ebitda: 연도별 EBITDA (이미 계산된 값) ``{연도: Decimal}``
        revenue: 연도별 매출액 ``{연도: Decimal | None}``

    Returns:
        연도별 EBITDA 마진(%) 딕셔너리 ``{연도: float}``.
    """
    result: dict[str, float] = {}

    for year, ebitda_val in ebitda.items():
        rev = revenue.get(year)

        if rev is None:
            logger.debug("EBITDA Margin 계산 건너뜀 (%s): 매출액이 None", year)
            continue

        if rev == Decimal("0"):
            logger.debug("EBITDA Margin 계산 건너뜀 (%s): 매출액이 0", year)
            continue

        result[year] = float(ebitda_val / rev * Decimal("100"))

    return result
