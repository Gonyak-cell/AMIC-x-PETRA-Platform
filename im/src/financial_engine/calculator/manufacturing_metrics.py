"""Financial Engine -- 제조업 산업별 재무 지표 계산기 (Phase B2).

제조업 핵심 KPI를 계산합니다:
OEE (설비종합효율), 가동률, 수율, 재고회전율, CAPEX/매출.

> 마지막 수정: 2026-02-11 15:10:00
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManufacturingMetrics:
    """제조업 산업별 재무 지표 데이터 클래스.

    각 필드는 ``{연도: 값}`` 형태의 딕셔너리입니다.
    계산이 불가능한 연도는 딕셔너리에서 제외됩니다.

    Attributes:
        oee: 설비종합효율 (%, float)
        capacity_utilization: CAPA 가동률 (%, float)
        yield_rate: 수율 (%, float)
        inventory_turnover: 재고회전율 (회, float)
        capex_to_revenue: CAPEX/매출 비율 (%, float)
    """

    oee: dict[str, float]
    capacity_utilization: dict[str, float]
    yield_rate: dict[str, float]
    inventory_turnover: dict[str, float]
    capex_to_revenue: dict[str, float]


# ---------------------------------------------------------------------------
# 개별 지표 계산 함수
# ---------------------------------------------------------------------------


def calculate_oee(
    availability: dict[str, Decimal | None],
    performance: dict[str, Decimal | None],
    quality: dict[str, Decimal | None],
) -> dict[str, float]:
    """설비종합효율(OEE)을 계산합니다.

    OEE = 가용률 × 성능효율 × 품질률 × 100

    입력값이 모두 1 초과(예: 90, 85, 95)이면 백분율로 간주하여
    각각 100으로 나눈 뒤 계산합니다.
    입력값이 0-1 범위이면 소수로 간주합니다.

    Args:
        availability: 연도별 가용률 ``{연도: Decimal | None}``
        performance: 연도별 성능효율 ``{연도: Decimal | None}``
        quality: 연도별 품질률 ``{연도: Decimal | None}``

    Returns:
        연도별 OEE(%) ``{연도: float}``.
        구성요소 중 None이 있는 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_oee(
        ...     availability={"2023": Decimal("0.90")},
        ...     performance={"2023": Decimal("0.85")},
        ...     quality={"2023": Decimal("0.95")},
        ... )
        {'2023': 72.675}
    """
    result: dict[str, float] = {}

    for year in availability:
        a = availability.get(year)
        p = performance.get(year)
        q = quality.get(year)

        if any(v is None for v in (a, p, q)):
            logger.debug("OEE 계산 건너뜀 (%s): 구성요소 None 포함", year)
            continue

        # 백분율 입력 감지: 모든 값이 1 초과이면 % 입력으로 간주
        if a > Decimal("1") and p > Decimal("1") and q > Decimal("1"):  # type: ignore[operator]
            a = a / Decimal("100")  # type: ignore[operator]
            p = p / Decimal("100")  # type: ignore[operator]
            q = q / Decimal("100")  # type: ignore[operator]

        oee_val = a * p * q * Decimal("100")  # type: ignore[operator]
        result[year] = float(oee_val)

    return result


def calculate_capacity_utilization(
    actual_output: dict[str, Decimal | None],
    max_capacity: dict[str, Decimal | None],
) -> dict[str, float]:
    """CAPA 가동률을 계산합니다.

    가동률 = 실제 생산량 / 최대 CAPA × 100

    Args:
        actual_output: 연도별 실제 생산량 ``{연도: Decimal | None}``
        max_capacity: 연도별 최대 생산 능력 ``{연도: Decimal | None}``

    Returns:
        연도별 가동률(%) ``{연도: float}``.
        최대 CAPA가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in actual_output:
        actual = actual_output.get(year)
        cap = max_capacity.get(year)

        if actual is None or cap is None:
            continue

        if cap == Decimal("0"):
            logger.debug("가동률 계산 건너뜀 (%s): 최대 CAPA가 0", year)
            continue

        result[year] = float(actual / cap * Decimal("100"))

    return result


def calculate_yield_rate(
    good_units: dict[str, Decimal | None],
    total_units: dict[str, Decimal | None],
) -> dict[str, float]:
    """수율을 계산합니다.

    수율 = 양품 수 / 총 생산 수 × 100

    Args:
        good_units: 연도별 양품 수 ``{연도: Decimal | None}``
        total_units: 연도별 총 생산 수 ``{연도: Decimal | None}``

    Returns:
        연도별 수율(%) ``{연도: float}``.
        총 생산 수가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in good_units:
        good = good_units.get(year)
        total = total_units.get(year)

        if good is None or total is None:
            continue

        if total == Decimal("0"):
            logger.debug("수율 계산 건너뜀 (%s): 총 생산 수가 0", year)
            continue

        result[year] = float(good / total * Decimal("100"))

    return result


def calculate_inventory_turnover(
    cogs: dict[str, Decimal | None],
    avg_inventory: dict[str, Decimal | None],
) -> dict[str, float]:
    """재고회전율을 계산합니다.

    재고회전율 = 매출원가(COGS) / 평균 재고자산 (회)

    Args:
        cogs: 연도별 매출원가 ``{연도: Decimal | None}``
        avg_inventory: 연도별 평균 재고자산 ``{연도: Decimal | None}``

    Returns:
        연도별 재고회전율(회) ``{연도: float}``.
        평균 재고가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in cogs:
        c = cogs.get(year)
        inv = avg_inventory.get(year)

        if c is None or inv is None:
            continue

        if inv == Decimal("0"):
            logger.debug("재고회전율 계산 건너뜀 (%s): 평균 재고가 0", year)
            continue

        result[year] = float(c / inv)

    return result


def calculate_capex_to_revenue(
    capex: dict[str, Decimal | None],
    revenue: dict[str, Decimal | None],
) -> dict[str, float]:
    """CAPEX/매출 비율을 계산합니다.

    CAPEX/매출 = |CAPEX| / 매출 × 100 (%)
    CapEx는 현금흐름표에서 음수로 보고될 수 있으므로 절대값을 사용합니다.

    Args:
        capex: 연도별 자본적 지출 ``{연도: Decimal | None}``
        revenue: 연도별 매출액 ``{연도: Decimal | None}``

    Returns:
        연도별 CAPEX/매출(%) ``{연도: float}``.
        매출이 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in capex:
        cx = capex.get(year)
        rev = revenue.get(year)

        if cx is None or rev is None:
            continue

        if rev == Decimal("0"):
            logger.debug("CAPEX/매출 계산 건너뜀 (%s): 매출이 0", year)
            continue

        result[year] = float(abs(cx) / rev * Decimal("100"))

    return result


# ---------------------------------------------------------------------------
# 통합 계산 함수
# ---------------------------------------------------------------------------


def calculate_manufacturing_metrics(
    revenue: dict[str, Decimal | None],
    cogs: dict[str, Decimal | None],
    capex: dict[str, Decimal | None],
    avg_inventory: dict[str, Decimal | None] | None = None,
    availability: dict[str, Decimal | None] | None = None,
    performance: dict[str, Decimal | None] | None = None,
    quality: dict[str, Decimal | None] | None = None,
    actual_output: dict[str, Decimal | None] | None = None,
    max_capacity: dict[str, Decimal | None] | None = None,
    good_units: dict[str, Decimal | None] | None = None,
    total_units: dict[str, Decimal | None] | None = None,
) -> ManufacturingMetrics:
    """제조업 산업별 재무 지표를 일괄 계산합니다.

    ``revenue``, ``cogs``, ``capex``는 필수(표준 계정)이며,
    나머지 산업 고유 입력은 선택입니다.
    선택 입력이 제공되지 않으면 해당 지표는 빈 딕셔너리로 반환됩니다.

    Args:
        revenue: 연도별 매출액 (mapped_data)
        cogs: 연도별 매출원가 (mapped_data)
        capex: 연도별 자본적 지출 (mapped_data)
        avg_inventory: 연도별 평균 재고자산 (mapped_data, 선택)
        availability: 연도별 가용률 (industry_data, 선택)
        performance: 연도별 성능효율 (industry_data, 선택)
        quality: 연도별 품질률 (industry_data, 선택)
        actual_output: 연도별 실제 생산량 (industry_data, 선택)
        max_capacity: 연도별 최대 생산 능력 (industry_data, 선택)
        good_units: 연도별 양품 수 (industry_data, 선택)
        total_units: 연도별 총 생산 수 (industry_data, 선택)

    Returns:
        ManufacturingMetrics: 계산된 제조업 지표 데이터 클래스.
    """
    # 1) OEE (선택 -- 3개 구성요소 모두 필요)
    oee: dict[str, float] = {}
    if all(v is not None for v in (availability, performance, quality)):
        oee = calculate_oee(availability, performance, quality)  # type: ignore[arg-type]

    # 2) 가동률 (선택)
    cap_util: dict[str, float] = {}
    if actual_output is not None and max_capacity is not None:
        cap_util = calculate_capacity_utilization(actual_output, max_capacity)

    # 3) 수율 (선택)
    yield_r: dict[str, float] = {}
    if good_units is not None and total_units is not None:
        yield_r = calculate_yield_rate(good_units, total_units)

    # 4) 재고회전율 (선택 -- avg_inventory 필요)
    inv_turn: dict[str, float] = {}
    if avg_inventory is not None:
        inv_turn = calculate_inventory_turnover(cogs, avg_inventory)

    # 5) CAPEX/매출 (필수 입력으로 항상 계산)
    capex_rev = calculate_capex_to_revenue(capex, revenue)

    return ManufacturingMetrics(
        oee=oee,
        capacity_utilization=cap_util,
        yield_rate=yield_r,
        inventory_turnover=inv_turn,
        capex_to_revenue=capex_rev,
    )
