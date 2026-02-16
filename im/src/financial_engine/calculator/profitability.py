"""Financial Engine -- Profitability Calculator (T-F06).

수익성 지표를 계산합니다: GPM, OPM, NPM, ROA, ROE.

> 마지막 수정: 2026-02-09 16:02:39
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProfitabilityMetrics:
    """수익성 지표 데이터 클래스.

    각 필드는 ``{연도: 비율(%)}`` 형태의 딕셔너리입니다.
    계산이 불가능한 연도(분모 0 또는 None)는 딕셔너리에서 제외됩니다.

    Attributes:
        gross_profit_margin: 매출총이익률 (%)
        operating_profit_margin: 영업이익률 (%)
        net_profit_margin: 순이익률 (%)
        roa: 총자산이익률 (%)
        roe: 자기자본이익률 (%)
    """

    gross_profit_margin: dict[str, float]
    operating_profit_margin: dict[str, float]
    net_profit_margin: dict[str, float]
    roa: dict[str, float]
    roe: dict[str, float]


def calculate_margin(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> float | None:
    """분자/분모로 백분율 마진을 계산합니다.

    Args:
        numerator: 분자 값 (예: 매출총이익, 영업이익, 순이익)
        denominator: 분모 값 (예: 매출액, 총자산, 자기자본)

    Returns:
        백분율(%) 값. 분자 또는 분모가 ``None``이거나 분모가 0이면 ``None``을 반환합니다.

    Examples:
        >>> calculate_margin(Decimal("150"), Decimal("1000"))
        15.0
        >>> calculate_margin(None, Decimal("1000"))
        >>> calculate_margin(Decimal("150"), Decimal("0"))
    """
    if numerator is None or denominator is None:
        return None
    if denominator == Decimal("0"):
        return None
    return float(numerator / denominator * Decimal("100"))


def calculate_profitability(
    revenue: dict[str, Decimal | None],
    gross_profit: dict[str, Decimal | None],
    operating_income: dict[str, Decimal | None],
    net_income: dict[str, Decimal | None],
    total_assets: dict[str, Decimal | None],
    total_equity: dict[str, Decimal | None],
) -> ProfitabilityMetrics:
    """수익성 지표를 일괄 계산합니다.

    ``revenue``에 포함된 모든 연도에 대해 다섯 가지 수익성 지표를 계산합니다.
    계산이 불가능한 연도(값이 ``None``이거나 분모가 0)는 결과 딕셔너리에서 제외됩니다.

    Args:
        revenue: 연도별 매출액 ``{연도: Decimal | None}``
        gross_profit: 연도별 매출총이익
        operating_income: 연도별 영업이익
        net_income: 연도별 당기순이익
        total_assets: 연도별 총자산
        total_equity: 연도별 자기자본

    Returns:
        ProfitabilityMetrics: 계산된 수익성 지표 데이터 클래스

    Examples:
        >>> from decimal import Decimal
        >>> result = calculate_profitability(
        ...     revenue={"2023": Decimal("1000"), "2024": Decimal("1200")},
        ...     gross_profit={"2023": Decimal("400"), "2024": Decimal("500")},
        ...     operating_income={"2023": Decimal("200"), "2024": Decimal("250")},
        ...     net_income={"2023": Decimal("150"), "2024": Decimal("180")},
        ...     total_assets={"2023": Decimal("5000"), "2024": Decimal("6000")},
        ...     total_equity={"2023": Decimal("3000"), "2024": Decimal("3500")},
        ... )
        >>> result.gross_profit_margin
        {'2023': 40.0, '2024': 41.666...}
    """
    gpm: dict[str, float] = {}
    opm: dict[str, float] = {}
    npm: dict[str, float] = {}
    roa_dict: dict[str, float] = {}
    roe_dict: dict[str, float] = {}

    for year in revenue:
        rev = revenue.get(year)

        # GPM = gross_profit / revenue * 100
        gp = gross_profit.get(year)
        gpm_val = calculate_margin(gp, rev)
        if gpm_val is not None:
            gpm[year] = gpm_val

        # OPM = operating_income / revenue * 100
        oi = operating_income.get(year)
        opm_val = calculate_margin(oi, rev)
        if opm_val is not None:
            opm[year] = opm_val

        # NPM = net_income / revenue * 100
        ni = net_income.get(year)
        npm_val = calculate_margin(ni, rev)
        if npm_val is not None:
            npm[year] = npm_val

        # ROA = net_income / total_assets * 100
        ta = total_assets.get(year)
        roa_val = calculate_margin(ni, ta)
        if roa_val is not None:
            roa_dict[year] = roa_val

        # ROE = net_income / total_equity * 100
        te = total_equity.get(year)
        roe_val = calculate_margin(ni, te)
        if roe_val is not None:
            roe_dict[year] = roe_val

    return ProfitabilityMetrics(
        gross_profit_margin=gpm,
        operating_profit_margin=opm,
        net_profit_margin=npm,
        roa=roa_dict,
        roe=roe_dict,
    )
