"""성장성 지표 계산기 (Growth Calculator).

> 마지막 수정: 2026-02-09 16:02:33

YoY(전년 대비 성장률), CAGR(연평균 성장률)을 산출합니다.
매출액, 영업이익, 당기순이익 등 주요 재무지표의 성장 추세를 분석하여
IM 문서의 Financial Analysis 섹션에 활용합니다.

사용 예시:
    from decimal import Decimal
    from src.financial_engine.calculator.growth import (
        calculate_growth,
        calculate_yoy,
        calculate_cagr,
    )

    # 단일 지표 YoY 계산
    revenue_by_year = {
        "2020": Decimal("100000"),
        "2021": Decimal("120000"),
        "2022": Decimal("135000"),
        "2023": Decimal("150000"),
    }
    yoy = calculate_yoy(revenue_by_year)
    # {"2021": 20.0, "2022": 12.5, "2023": 11.11...}

    # CAGR 계산
    cagr = calculate_cagr(Decimal("100"), Decimal("150"), 3)
    # 약 14.47

    # 전체 성장성 지표 계산
    metrics = {
        "revenue": revenue_by_year,
        "operating_income": {...},
    }
    growth = calculate_growth(metrics)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GrowthMetrics:
    """성장성 지표 결과.

    Attributes:
        yoy: 지표별 연도별 YoY 성장률 (%). {metric_name: {year: yoy%}}
        cagr_3y: 지표별 3년 CAGR (%). {metric_name: cagr}
        cagr_5y: 지표별 5년 CAGR (%). {metric_name: cagr}
    """

    yoy: dict[str, dict[str, float]]
    cagr_3y: dict[str, float]
    cagr_5y: dict[str, float]


def calculate_yoy(values: dict[str, Decimal]) -> dict[str, float]:
    """연도별 YoY(전년 대비) 성장률을 계산합니다.

    연도를 오름차순으로 정렬한 후, 연속된 연도 쌍에 대해
    (당기 - 전기) / |전기| * 100 으로 백분율을 계산합니다.

    Args:
        values: 연도별 값 딕셔너리. 키는 연도 문자열(예: "2023"),
            값은 해당 연도의 재무 수치(Decimal).

    Returns:
        연도별 YoY 성장률(%) 딕셔너리. 키는 당기 연도 문자열.
        단일 연도 데이터인 경우 빈 딕셔너리를 반환합니다.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_yoy({"2022": Decimal("100"), "2023": Decimal("120")})
        {'2023': 20.0}
        >>> calculate_yoy({"2023": Decimal("100")})
        {}
    """
    if len(values) < 2:
        return {}

    sorted_years = sorted(values.keys())
    result: dict[str, float] = {}

    for i in range(1, len(sorted_years)):
        prev_year = sorted_years[i - 1]
        curr_year = sorted_years[i]
        prev_value = values[prev_year]
        curr_value = values[curr_year]

        yoy = _compute_yoy(prev_value, curr_value)
        if yoy is not None:
            result[curr_year] = yoy
        else:
            logger.warning(
                "YoY 계산 불가: %s -> %s (전기값=%s, 당기값=%s)",
                prev_year,
                curr_year,
                prev_value,
                curr_value,
            )

    return result


def calculate_cagr(
    start_value: Decimal,
    end_value: Decimal,
    years: int,
) -> float | None:
    """CAGR(연평균 성장률)을 계산합니다.

    CAGR = ((end_value / start_value) ** (1 / years) - 1) * 100

    Args:
        start_value: 시작 연도의 값.
        end_value: 종료 연도의 값.
        years: 기간 (연 수). 양의 정수여야 합니다.

    Returns:
        CAGR 백분율(%). 계산이 불가능한 경우 None을 반환합니다.
        - start_value가 0인 경우
        - start_value가 음수이고 end_value가 양수인 경우 (부호 전환)
        - years가 0 이하인 경우

    Examples:
        >>> from decimal import Decimal
        >>> cagr = calculate_cagr(Decimal("100"), Decimal("150"), 3)
        >>> round(cagr, 2)
        14.47
        >>> calculate_cagr(Decimal("0"), Decimal("100"), 3) is None
        True
    """
    if years <= 0:
        logger.warning("CAGR 계산 불가: years=%d (양의 정수 필요)", years)
        return None

    if start_value == Decimal("0"):
        logger.warning("CAGR 계산 불가: 시작값이 0")
        return None

    # 시작값이 음수이고 종료값이 양수인 경우 (부호 전환) -> 정의 불가
    if start_value < Decimal("0") and end_value > Decimal("0"):
        logger.warning(
            "CAGR 계산 불가: 부호 전환 (start=%s, end=%s)",
            start_value,
            end_value,
        )
        return None

    # 시작값이 양수이고 종료값이 음수인 경우 (부호 전환) -> 정의 불가
    if start_value > Decimal("0") and end_value < Decimal("0"):
        logger.warning(
            "CAGR 계산 불가: 부호 전환 (start=%s, end=%s)",
            start_value,
            end_value,
        )
        return None

    # 둘 다 음수인 경우: 절대값 기준으로 계산 후 부호 반전
    # 예: -200 -> -100 은 실질적으로 개선(50% 감소), CAGR은 양수로 표현
    if start_value < Decimal("0") and end_value < Decimal("0"):
        abs_start = abs(start_value)
        abs_end = abs(end_value)
        ratio = float(abs_end / abs_start)
        # 손실이 줄어들면 양의 성장, 늘어나면 음의 성장
        cagr = (ratio ** (1.0 / years) - 1.0) * 100.0
        # 부호 반전: 음수 절대값이 줄어드는 것은 개선(양의 성장)
        return -cagr

    # 일반적인 경우 (둘 다 양수)
    ratio = float(end_value / start_value)
    cagr = (ratio ** (1.0 / years) - 1.0) * 100.0
    return cagr


def calculate_growth(
    metrics: dict[str, dict[str, Decimal]],
) -> GrowthMetrics:
    """여러 재무지표에 대한 성장성 지표를 일괄 계산합니다.

    각 지표에 대해 YoY 성장률, 3년 CAGR, 5년 CAGR을 산출합니다.

    Args:
        metrics: 지표별 연도별 값 딕셔너리.
            키는 지표명(예: "revenue", "operating_income"),
            값은 연도별 Decimal 값 딕셔너리.

    Returns:
        GrowthMetrics: 모든 지표의 성장성 분석 결과.
            - yoy: 지표별 YoY 성장률
            - cagr_3y: 3년 이상 데이터가 있는 지표의 3년 CAGR
            - cagr_5y: 5년 이상 데이터가 있는 지표의 5년 CAGR

    Examples:
        >>> from decimal import Decimal
        >>> metrics = {
        ...     "revenue": {
        ...         "2019": Decimal("80000"),
        ...         "2020": Decimal("100000"),
        ...         "2021": Decimal("120000"),
        ...         "2022": Decimal("135000"),
        ...         "2023": Decimal("150000"),
        ...     },
        ... }
        >>> result = calculate_growth(metrics)
        >>> "revenue" in result.yoy
        True
        >>> "revenue" in result.cagr_3y
        True
        >>> "revenue" in result.cagr_5y
        False
    """
    yoy_all: dict[str, dict[str, float]] = {}
    cagr_3y_all: dict[str, float] = {}
    cagr_5y_all: dict[str, float] = {}

    for metric_name, yearly_values in metrics.items():
        if not yearly_values:
            logger.warning("성장성 계산 건너뜀: '%s' 데이터 없음", metric_name)
            continue

        # YoY 계산
        yoy_result = calculate_yoy(yearly_values)
        yoy_all[metric_name] = yoy_result

        # 연도 정렬
        sorted_years = sorted(yearly_values.keys())
        num_years = len(sorted_years)

        # 3년 CAGR (최소 4개 데이터 포인트 필요: 시작 + 3년)
        if num_years >= 4:
            start_year_3y = sorted_years[-4]
            end_year_3y = sorted_years[-1]
            cagr_3y = calculate_cagr(
                yearly_values[start_year_3y],
                yearly_values[end_year_3y],
                3,
            )
            if cagr_3y is not None:
                cagr_3y_all[metric_name] = cagr_3y

        # 5년 CAGR (최소 6개 데이터 포인트 필요: 시작 + 5년)
        if num_years >= 6:
            start_year_5y = sorted_years[-6]
            end_year_5y = sorted_years[-1]
            cagr_5y = calculate_cagr(
                yearly_values[start_year_5y],
                yearly_values[end_year_5y],
                5,
            )
            if cagr_5y is not None:
                cagr_5y_all[metric_name] = cagr_5y

    return GrowthMetrics(
        yoy=yoy_all,
        cagr_3y=cagr_3y_all,
        cagr_5y=cagr_5y_all,
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼 함수
# ---------------------------------------------------------------------------


def _compute_yoy(prev_value: Decimal, curr_value: Decimal) -> float | None:
    """단일 연도 쌍의 YoY 성장률을 계산합니다.

    YoY = (curr - prev) / |prev| * 100

    Args:
        prev_value: 전기 값.
        curr_value: 당기 값.

    Returns:
        YoY 성장률(%). 전기값이 0이면 None.
    """
    if prev_value == Decimal("0"):
        return None

    yoy = float((curr_value - prev_value) / abs(prev_value)) * 100.0
    return yoy
