"""Financial Engine -- Leverage Calculator (T-F09).

레버리지(부채) 지표를 계산합니다: D/E, ICR, Net Debt/EBITDA.

> 마지막 수정: 2026-02-09 16:08:56
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LeverageMetrics:
    """레버리지 지표 데이터 클래스.

    각 필드는 ``{연도: 비율}`` 형태의 딕셔너리입니다.
    계산이 불가능한 연도(분모 0 또는 None)는 딕셔너리에서 제외됩니다.

    Attributes:
        debt_to_equity: 부채비율 (D/E Ratio, 배수)
        interest_coverage: 이자보상배율 (ICR, 배수)
        net_debt_to_ebitda: 순부채/EBITDA (배수, 부채 상환 소요 연수)
    """

    debt_to_equity: dict[str, float]
    interest_coverage: dict[str, float]
    net_debt_to_ebitda: dict[str, float]


def _compute_ratio(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> float | None:
    """분자/분모로 비율을 계산합니다 (백분율이 아닌 배수).

    Args:
        numerator: 분자 값.
        denominator: 분모 값.

    Returns:
        비율(배수) 값. 분자 또는 분모가 ``None``이거나 분모가 0이면
        ``None``을 반환합니다.
    """
    if numerator is None or denominator is None:
        return None
    if denominator == Decimal("0"):
        return None
    return float(numerator / denominator)


def calculate_debt_to_equity(
    total_liabilities: dict[str, Decimal | None],
    total_equity: dict[str, Decimal | None],
) -> dict[str, float]:
    """연도별 부채비율(D/E Ratio)을 계산합니다.

    D/E = total_liabilities / total_equity (배수).
    자기자본이 음수인 경우에도 계산을 수행합니다 (결과가 음수).
    분모(total_equity)가 0 또는 ``None``이면 해당 연도는 제외됩니다.

    Args:
        total_liabilities: 연도별 총부채 ``{연도: Decimal | None}``
        total_equity: 연도별 자기자본 ``{연도: Decimal | None}``

    Returns:
        연도별 D/E Ratio 딕셔너리. 계산 불가 연도는 제외.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_debt_to_equity(
        ...     {"2023": Decimal("500")},
        ...     {"2023": Decimal("1000")},
        ... )
        {'2023': 0.5}
        >>> calculate_debt_to_equity(
        ...     {"2023": Decimal("500")},
        ...     {"2023": Decimal("0")},
        ... )
        {}
    """
    result: dict[str, float] = {}
    for year in total_liabilities:
        liab = total_liabilities.get(year)
        eq = total_equity.get(year)
        ratio = _compute_ratio(liab, eq)
        if ratio is not None:
            result[year] = ratio
    return result


def calculate_interest_coverage(
    operating_income: dict[str, Decimal | None],
    interest_expense: dict[str, Decimal | None],
) -> dict[str, float]:
    """연도별 이자보상배율(ICR)을 계산합니다.

    ICR = operating_income / interest_expense (배수).
    분모(interest_expense)가 0 또는 ``None``이면 해당 연도는 제외됩니다.

    Args:
        operating_income: 연도별 영업이익 ``{연도: Decimal | None}``
        interest_expense: 연도별 이자비용 ``{연도: Decimal | None}``

    Returns:
        연도별 ICR 딕셔너리. 계산 불가 연도는 제외.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_interest_coverage(
        ...     {"2023": Decimal("300")},
        ...     {"2023": Decimal("100")},
        ... )
        {'2023': 3.0}
        >>> calculate_interest_coverage(
        ...     {"2023": Decimal("300")},
        ...     {"2023": Decimal("0")},
        ... )
        {}
    """
    result: dict[str, float] = {}
    for year in operating_income:
        oi = operating_income.get(year)
        ie = interest_expense.get(year)
        ratio = _compute_ratio(oi, ie)
        if ratio is not None:
            result[year] = ratio
    return result


def _calculate_net_debt_to_ebitda(
    total_debt: dict[str, Decimal | None],
    cash_and_equivalents: dict[str, Decimal | None],
    ebitda: dict[str, Decimal | None],
) -> dict[str, float]:
    """연도별 순부채/EBITDA 비율을 계산합니다.

    Net Debt/EBITDA = (total_debt - cash_and_equivalents) / ebitda (배수).
    분모(ebitda)가 0 또는 ``None``이면 해당 연도는 제외됩니다.
    분자 구성 요소(total_debt 또는 cash_and_equivalents)가 ``None``이면 제외됩니다.

    Args:
        total_debt: 연도별 총차입금 ``{연도: Decimal | None}``
        cash_and_equivalents: 연도별 현금및현금성자산 ``{연도: Decimal | None}``
        ebitda: 연도별 EBITDA ``{연도: Decimal | None}``

    Returns:
        연도별 Net Debt/EBITDA 딕셔너리. 계산 불가 연도는 제외.
    """
    result: dict[str, float] = {}
    for year in total_debt:
        debt = total_debt.get(year)
        cash = cash_and_equivalents.get(year)
        ebitda_val = ebitda.get(year)

        if debt is None or cash is None or ebitda_val is None:
            continue
        if ebitda_val == Decimal("0"):
            continue

        net_debt = debt - cash
        result[year] = float(net_debt / ebitda_val)
    return result


def calculate_leverage(
    total_liabilities: dict[str, Decimal | None],
    total_equity: dict[str, Decimal | None],
    operating_income: dict[str, Decimal | None],
    interest_expense: dict[str, Decimal | None],
    total_debt: dict[str, Decimal | None] | None = None,
    cash_and_equivalents: dict[str, Decimal | None] | None = None,
    ebitda: dict[str, Decimal | None] | None = None,
) -> LeverageMetrics:
    """레버리지 지표를 일괄 계산합니다.

    세 가지 레버리지 지표(D/E, ICR, Net Debt/EBITDA)를 한 번에 계산합니다.
    ``total_debt``, ``cash_and_equivalents``, ``ebitda``가 모두 제공된 경우에만
    Net Debt/EBITDA를 계산하며, 하나라도 ``None``이면 빈 딕셔너리를 반환합니다.

    Args:
        total_liabilities: 연도별 총부채 ``{연도: Decimal | None}``
        total_equity: 연도별 자기자본 ``{연도: Decimal | None}``
        operating_income: 연도별 영업이익 ``{연도: Decimal | None}``
        interest_expense: 연도별 이자비용 ``{연도: Decimal | None}``
        total_debt: 연도별 총차입금. Net Debt/EBITDA 계산에 사용.
        cash_and_equivalents: 연도별 현금및현금성자산. Net Debt/EBITDA 계산에 사용.
        ebitda: 연도별 EBITDA. Net Debt/EBITDA 계산에 사용.

    Returns:
        LeverageMetrics: 계산된 레버리지 지표 데이터 클래스.

    Examples:
        >>> from decimal import Decimal
        >>> result = calculate_leverage(
        ...     total_liabilities={"2023": Decimal("500"), "2024": Decimal("600")},
        ...     total_equity={"2023": Decimal("1000"), "2024": Decimal("1200")},
        ...     operating_income={"2023": Decimal("200"), "2024": Decimal("250")},
        ...     interest_expense={"2023": Decimal("50"), "2024": Decimal("60")},
        ...     total_debt={"2023": Decimal("400"), "2024": Decimal("500")},
        ...     cash_and_equivalents={"2023": Decimal("100"), "2024": Decimal("150")},
        ...     ebitda={"2023": Decimal("300"), "2024": Decimal("350")},
        ... )
        >>> result.debt_to_equity
        {'2023': 0.5, '2024': 0.5}
        >>> result.interest_coverage
        {'2023': 4.0, '2024': 4.166...}
        >>> result.net_debt_to_ebitda
        {'2023': 1.0, '2024': 1.0}
    """
    de = calculate_debt_to_equity(total_liabilities, total_equity)
    icr = calculate_interest_coverage(operating_income, interest_expense)

    # Net Debt/EBITDA: 세 인자가 모두 제공된 경우에만 계산
    if (
        total_debt is not None
        and cash_and_equivalents is not None
        and ebitda is not None
    ):
        nd_ebitda = _calculate_net_debt_to_ebitda(
            total_debt, cash_and_equivalents, ebitda
        )
    else:
        nd_ebitda = {}

    return LeverageMetrics(
        debt_to_equity=de,
        interest_coverage=icr,
        net_debt_to_ebitda=nd_ebitda,
    )
