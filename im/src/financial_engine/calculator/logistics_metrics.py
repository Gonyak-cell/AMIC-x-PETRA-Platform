"""Financial Engine -- 물류/운송 산업별 재무 지표 계산기 (Phase B3).

물류/운송 핵심 KPI를 계산합니다:
정시 배송률, 플릿 가동률, 톤km당 매출, 건당 비용.

> 마지막 수정: 2026-02-11 15:20:00
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LogisticsMetrics:
    """물류/운송 산업별 재무 지표 데이터 클래스.

    각 필드는 ``{연도: 값}`` 형태의 딕셔너리입니다.
    계산이 불가능한 연도는 딕셔너리에서 제외됩니다.

    Attributes:
        on_time_delivery: 정시 배송률 (%, float)
        fleet_utilization: 플릿 가동률 (%, float)
        revenue_per_tonkm: 톤km당 매출 (Decimal, 금액)
        cost_per_delivery: 건당 비용 (Decimal, 금액)
    """

    on_time_delivery: dict[str, float]
    fleet_utilization: dict[str, float]
    revenue_per_tonkm: dict[str, Decimal]
    cost_per_delivery: dict[str, Decimal]


# ---------------------------------------------------------------------------
# 개별 지표 계산 함수
# ---------------------------------------------------------------------------


def calculate_on_time_delivery(
    on_time_count: dict[str, Decimal | None],
    total_deliveries: dict[str, Decimal | None],
) -> dict[str, float]:
    """정시 배송률을 계산합니다.

    정시 배송률 = 정시 배송 건수 / 총 배송 건수 × 100

    Args:
        on_time_count: 연도별 정시 배송 건수 ``{연도: Decimal | None}``
        total_deliveries: 연도별 총 배송 건수 ``{연도: Decimal | None}``

    Returns:
        연도별 정시 배송률(%) ``{연도: float}``.
        총 배송 건수가 0 또는 None인 연도는 제외됩니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_on_time_delivery(
        ...     on_time_count={"2023": Decimal("950")},
        ...     total_deliveries={"2023": Decimal("1000")},
        ... )
        {'2023': 95.0}
    """
    result: dict[str, float] = {}

    for year in on_time_count:
        otc = on_time_count.get(year)
        td = total_deliveries.get(year)

        if otc is None or td is None:
            continue

        if td == Decimal("0"):
            logger.debug("정시 배송률 계산 건너뜀 (%s): 총 배송 건수가 0", year)
            continue

        result[year] = float(otc / td * Decimal("100"))

    return result


def calculate_fleet_utilization(
    active_fleet: dict[str, Decimal | None],
    total_fleet: dict[str, Decimal | None],
) -> dict[str, float]:
    """플릿 가동률을 계산합니다.

    플릿 가동률 = 가동 차량 수 / 보유 차량 수 × 100

    Args:
        active_fleet: 연도별 가동 차량 수 ``{연도: Decimal | None}``
        total_fleet: 연도별 보유 차량 수 ``{연도: Decimal | None}``

    Returns:
        연도별 플릿 가동률(%) ``{연도: float}``.
        보유 차량 수가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in active_fleet:
        af = active_fleet.get(year)
        tf = total_fleet.get(year)

        if af is None or tf is None:
            continue

        if tf == Decimal("0"):
            logger.debug("플릿 가동률 계산 건너뜀 (%s): 보유 차량 수가 0", year)
            continue

        result[year] = float(af / tf * Decimal("100"))

    return result


def calculate_revenue_per_tonkm(
    transport_revenue: dict[str, Decimal | None],
    total_tonkm: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """톤km당 매출을 계산합니다.

    톤km당 매출 = 운송 매출 / 총 톤km

    Args:
        transport_revenue: 연도별 운송 매출 ``{연도: Decimal | None}``
        total_tonkm: 연도별 총 톤km ``{연도: Decimal | None}``

    Returns:
        연도별 톤km당 매출 ``{연도: Decimal}``.
        총 톤km가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, Decimal] = {}

    for year in transport_revenue:
        rev = transport_revenue.get(year)
        tkm = total_tonkm.get(year)

        if rev is None or tkm is None:
            continue

        if tkm == Decimal("0"):
            logger.debug("톤km당 매출 계산 건너뜀 (%s): 총 톤km가 0", year)
            continue

        result[year] = rev / tkm

    return result


def calculate_cost_per_delivery(
    operating_cost: dict[str, Decimal | None],
    total_deliveries: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """건당 비용을 계산합니다.

    건당 비용 = 총 운영비용 / 총 배송 건수

    Args:
        operating_cost: 연도별 총 운영비용 ``{연도: Decimal | None}``
        total_deliveries: 연도별 총 배송 건수 ``{연도: Decimal | None}``

    Returns:
        연도별 건당 비용 ``{연도: Decimal}``.
        총 배송 건수가 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, Decimal] = {}

    for year in operating_cost:
        cost = operating_cost.get(year)
        td = total_deliveries.get(year)

        if cost is None or td is None:
            continue

        if td == Decimal("0"):
            logger.debug("건당 비용 계산 건너뜀 (%s): 총 배송 건수가 0", year)
            continue

        result[year] = cost / td

    return result


# ---------------------------------------------------------------------------
# 통합 계산 함수
# ---------------------------------------------------------------------------


def calculate_logistics_metrics(
    revenue: dict[str, Decimal | None],
    on_time_count: dict[str, Decimal | None] | None = None,
    total_deliveries: dict[str, Decimal | None] | None = None,
    active_fleet: dict[str, Decimal | None] | None = None,
    total_fleet: dict[str, Decimal | None] | None = None,
    transport_revenue: dict[str, Decimal | None] | None = None,
    total_tonkm: dict[str, Decimal | None] | None = None,
    operating_cost: dict[str, Decimal | None] | None = None,
) -> LogisticsMetrics:
    """물류/운송 산업별 재무 지표를 일괄 계산합니다.

    ``revenue``는 필수이며, 나머지 입력은 선택입니다.
    선택 입력이 제공되지 않으면 해당 지표는 빈 딕셔너리로 반환됩니다.

    Args:
        revenue: 연도별 매출액 (mapped_data)
        on_time_count: 연도별 정시 배송 건수 (industry_data, 선택)
        total_deliveries: 연도별 총 배송 건수 (industry_data, 선택)
        active_fleet: 연도별 가동 차량 수 (industry_data, 선택)
        total_fleet: 연도별 보유 차량 수 (industry_data, 선택)
        transport_revenue: 연도별 운송 매출 (industry_data, 선택)
        total_tonkm: 연도별 총 톤km (industry_data, 선택)
        operating_cost: 연도별 총 운영비용 (industry_data, 선택)

    Returns:
        LogisticsMetrics: 계산된 물류 지표 데이터 클래스.
    """
    # 1) 정시 배송률 (선택)
    otd: dict[str, float] = {}
    if on_time_count is not None and total_deliveries is not None:
        otd = calculate_on_time_delivery(on_time_count, total_deliveries)

    # 2) 플릿 가동률 (선택)
    fleet_util: dict[str, float] = {}
    if active_fleet is not None and total_fleet is not None:
        fleet_util = calculate_fleet_utilization(active_fleet, total_fleet)

    # 3) 톤km당 매출 (선택)
    rev_tonkm: dict[str, Decimal] = {}
    if transport_revenue is not None and total_tonkm is not None:
        rev_tonkm = calculate_revenue_per_tonkm(transport_revenue, total_tonkm)

    # 4) 건당 비용 (선택)
    cost_del: dict[str, Decimal] = {}
    if operating_cost is not None and total_deliveries is not None:
        cost_del = calculate_cost_per_delivery(operating_cost, total_deliveries)

    return LogisticsMetrics(
        on_time_delivery=otd,
        fleet_utilization=fleet_util,
        revenue_per_tonkm=rev_tonkm,
        cost_per_delivery=cost_del,
    )
