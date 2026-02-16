"""Financial Engine -- 헬스케어/바이오 산업별 재무 지표 계산기 (Phase B3).

헬스케어/바이오 핵심 KPI를 계산합니다:
rNPV (위험조정 순현재가치), 단계별 성공률, 특허 잔여기간, R&D/매출.

> 마지막 수정: 2026-02-11 15:20:00
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HealthcareMetrics:
    """헬스케어/바이오 산업별 재무 지표 데이터 클래스.

    각 필드는 ``{연도 또는 단계: 값}`` 형태의 딕셔너리입니다.
    계산이 불가능한 항목은 딕셔너리에서 제외됩니다.

    Attributes:
        rnpv: 위험조정 순현재가치 (Decimal, 금액)
        phase_success_rates: 단계별 성공률 (%, float)
        patent_remaining_years: 특허 잔여기간 (년, float)
        rd_to_revenue: R&D/매출 비율 (%, float)
    """

    rnpv: dict[str, Decimal]
    phase_success_rates: dict[str, float]
    patent_remaining_years: dict[str, float]
    rd_to_revenue: dict[str, float]


# ---------------------------------------------------------------------------
# 개별 지표 계산 함수
# ---------------------------------------------------------------------------


def calculate_rnpv(
    expected_cash_flows: dict[str, Decimal | None],
    success_probabilities: dict[str, Decimal | None],
    discount_rate: Decimal,
) -> dict[str, Decimal]:
    """위험조정 순현재가치(rNPV)를 계산합니다.

    rNPV_t = CF_t × P_success_t / (1 + r)^t

    각 키(연도 또는 단계)에 대해 개별 할인 rNPV를 계산합니다.
    키는 정수로 변환 가능해야 하며, 할인 지수로 사용됩니다.

    Args:
        expected_cash_flows: 단계/연도별 기대 현금흐름 ``{키: Decimal | None}``
        success_probabilities: 단계/연도별 성공 확률 (소수) ``{키: Decimal | None}``
        discount_rate: 할인율 (소수, 예: 0.10 = 10%)

    Returns:
        단계/연도별 rNPV ``{키: Decimal}``.
        입력값이 None이거나 할인율이 음수인 경우 제외됩니다.
    """
    if discount_rate < Decimal("0"):
        logger.warning("rNPV 계산 불가: 할인율이 음수 (%s)", discount_rate)
        return {}

    result: dict[str, Decimal] = {}
    one = Decimal("1")

    for key in expected_cash_flows:
        cf = expected_cash_flows.get(key)
        prob = success_probabilities.get(key)

        if cf is None or prob is None:
            logger.debug("rNPV 계산 건너뜀 (%s): 입력값 None", key)
            continue

        try:
            t = int(key)
        except ValueError:
            logger.debug("rNPV 계산 건너뜀 (%s): 정수 변환 불가", key)
            continue

        discount_factor = (one + discount_rate) ** t
        if discount_factor == Decimal("0"):
            continue

        result[key] = cf * prob / discount_factor

    return result


def calculate_phase_success_rates(
    phase_data: dict[str, Decimal | None],
) -> dict[str, float]:
    """단계별 성공률을 반환합니다.

    입력 데이터를 Decimal에서 float로 변환합니다 (pass-through).
    None인 단계는 제외됩니다.

    Args:
        phase_data: 단계별 성공률 ``{단계명: Decimal | None}``
            예: {"Phase I": Decimal("0.65"), "Phase II": Decimal("0.35")}

    Returns:
        단계별 성공률(%) ``{단계명: float}``.
    """
    result: dict[str, float] = {}
    for phase, rate in phase_data.items():
        if rate is not None:
            result[phase] = float(rate)
    return result


def calculate_patent_remaining(
    patent_expiry_years: dict[str, Decimal | None],
    current_year: int,
) -> dict[str, float]:
    """특허 잔여기간을 계산합니다.

    잔여기간 = 만료연도 - 현재연도

    음수(이미 만료)인 경우 결과에서 제외됩니다.

    Args:
        patent_expiry_years: 제품/특허별 만료연도 ``{제품명: Decimal | None}``
        current_year: 현재 연도 (정수)

    Returns:
        제품/특허별 잔여기간(년) ``{제품명: float}``.
        만료된 특허(음수)는 제외됩니다.
    """
    result: dict[str, float] = {}
    for product, expiry in patent_expiry_years.items():
        if expiry is None:
            continue
        remaining = float(expiry) - current_year
        if remaining < 0:
            logger.debug(
                "특허 잔여기간 건너뜀 (%s): 이미 만료 (잔여 %.1f년)", product, remaining
            )
            continue
        result[product] = remaining
    return result


def calculate_rd_to_revenue(
    rd_expense: dict[str, Decimal | None],
    revenue: dict[str, Decimal | None],
) -> dict[str, float]:
    """R&D/매출 비율을 계산합니다.

    R&D/매출 = R&D비 / 매출 × 100 (%)

    Args:
        rd_expense: 연도별 연구개발비 ``{연도: Decimal | None}``
        revenue: 연도별 매출액 ``{연도: Decimal | None}``

    Returns:
        연도별 R&D/매출(%) ``{연도: float}``.
        매출이 0 또는 None인 연도는 제외됩니다.
    """
    result: dict[str, float] = {}

    for year in rd_expense:
        rd = rd_expense.get(year)
        rev = revenue.get(year)

        if rd is None or rev is None:
            continue

        if rev == Decimal("0"):
            logger.debug("R&D/매출 계산 건너뜀 (%s): 매출이 0", year)
            continue

        result[year] = float(rd / rev * Decimal("100"))

    return result


# ---------------------------------------------------------------------------
# 통합 계산 함수
# ---------------------------------------------------------------------------


def calculate_healthcare_metrics(
    revenue: dict[str, Decimal | None],
    rd_expense: dict[str, Decimal | None] | None = None,
    expected_cash_flows: dict[str, Decimal | None] | None = None,
    success_probabilities: dict[str, Decimal | None] | None = None,
    discount_rate: Decimal | None = None,
    phase_data: dict[str, Decimal | None] | None = None,
    patent_expiry_years: dict[str, Decimal | None] | None = None,
    current_year: int | None = None,
) -> HealthcareMetrics:
    """헬스케어/바이오 산업별 재무 지표를 일괄 계산합니다.

    ``revenue``는 필수이며, 나머지 입력은 선택입니다.
    선택 입력이 제공되지 않으면 해당 지표는 빈 딕셔너리로 반환됩니다.

    Args:
        revenue: 연도별 매출액 (mapped_data)
        rd_expense: 연도별 연구개발비 (mapped_data, 선택)
        expected_cash_flows: 단계별 기대 현금흐름 (industry_data, 선택)
        success_probabilities: 단계별 성공 확률 (industry_data, 선택)
        discount_rate: 할인율, 소수 (industry_data, 선택)
        phase_data: 단계별 성공률 (industry_data, 선택)
        patent_expiry_years: 제품별 특허 만료연도 (industry_data, 선택)
        current_year: 현재 연도 (선택)

    Returns:
        HealthcareMetrics: 계산된 헬스케어 지표 데이터 클래스.
    """
    # 1) rNPV (선택 -- CF, 확률, 할인율 모두 필요)
    rnpv: dict[str, Decimal] = {}
    if all(
        v is not None
        for v in (expected_cash_flows, success_probabilities, discount_rate)
    ):
        rnpv = calculate_rnpv(
            expected_cash_flows, success_probabilities, discount_rate  # type: ignore[arg-type]
        )

    # 2) 단계별 성공률 (선택)
    phase_rates: dict[str, float] = {}
    if phase_data is not None:
        phase_rates = calculate_phase_success_rates(phase_data)

    # 3) 특허 잔여기간 (선택)
    patent_remaining: dict[str, float] = {}
    if patent_expiry_years is not None and current_year is not None:
        patent_remaining = calculate_patent_remaining(
            patent_expiry_years, current_year
        )

    # 4) R&D/매출 (선택 -- rd_expense 필요)
    rd_rev: dict[str, float] = {}
    if rd_expense is not None:
        rd_rev = calculate_rd_to_revenue(rd_expense, revenue)

    return HealthcareMetrics(
        rnpv=rnpv,
        phase_success_rates=phase_rates,
        patent_remaining_years=patent_remaining,
        rd_to_revenue=rd_rev,
    )
