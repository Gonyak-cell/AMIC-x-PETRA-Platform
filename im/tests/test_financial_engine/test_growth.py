"""성장성 지표 계산기(Growth Calculator) 단위 테스트.

YoY(전년 대비 성장률), CAGR(연평균 성장률) 계산을 검증합니다.

> 마지막 수정: 2026-02-09 16:28:44
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.growth import (
    GrowthMetrics,
    calculate_cagr,
    calculate_growth,
    calculate_yoy,
)


# ---------------------------------------------------------------------------
# calculate_yoy 테스트
# ---------------------------------------------------------------------------


class TestCalculateYoY:
    """calculate_yoy 함수 테스트."""

    def test_basic_yoy(self) -> None:
        """기본 YoY 계산: 100→120 = 20.0%."""
        values = {"2022": Decimal("100"), "2023": Decimal("120")}
        result = calculate_yoy(values)
        assert result == {"2023": pytest.approx(20.0)}

    def test_zero_prev_skipped(self) -> None:
        """전기값이 0이면 해당 연도를 건너뛴다."""
        values = {"2022": Decimal("0"), "2023": Decimal("120")}
        result = calculate_yoy(values)
        assert "2023" not in result

    def test_negative_values(self) -> None:
        """음수 값 처리: -100→-50 = 50.0% (개선)."""
        values = {"2022": Decimal("-100"), "2023": Decimal("-50")}
        result = calculate_yoy(values)
        # YoY = (-50 - (-100)) / |-100| * 100 = 50 / 100 * 100 = 50.0%
        assert result["2023"] == pytest.approx(50.0)

    def test_single_year_returns_empty(self) -> None:
        """단일 연도 데이터는 빈 딕셔너리를 반환한다."""
        values = {"2023": Decimal("100")}
        result = calculate_yoy(values)
        assert result == {}


# ---------------------------------------------------------------------------
# calculate_cagr 테스트
# ---------------------------------------------------------------------------


class TestCalculateCAGR:
    """calculate_cagr 함수 테스트."""

    def test_basic_cagr(self) -> None:
        """기본 CAGR 계산: (150/100)^(1/3)-1 ≈ 14.47%."""
        result = calculate_cagr(Decimal("100"), Decimal("150"), 3)
        assert result is not None
        assert result == pytest.approx(14.47, abs=0.01)

    def test_zero_start_returns_none(self) -> None:
        """시작값이 0이면 None을 반환한다."""
        result = calculate_cagr(Decimal("0"), Decimal("150"), 3)
        assert result is None

    def test_sign_change_positive_to_negative_returns_none(self) -> None:
        """양수→음수 부호 전환 시 None을 반환한다."""
        result = calculate_cagr(Decimal("100"), Decimal("-50"), 3)
        assert result is None

    def test_sign_change_negative_to_positive_returns_none(self) -> None:
        """음수→양수 부호 전환 시 None을 반환한다."""
        result = calculate_cagr(Decimal("-100"), Decimal("50"), 3)
        assert result is None

    def test_both_negative(self) -> None:
        """둘 다 음수: -200→-100 (손실 감소, 부호 반전 로직 적용)."""
        result = calculate_cagr(Decimal("-200"), Decimal("-100"), 3)
        assert result is not None
        # 절대값 기준: (100/200)^(1/3)-1 ≈ -20.63% → 부호 반전 → 20.63%
        assert result == pytest.approx(20.63, abs=0.01)


# ---------------------------------------------------------------------------
# calculate_growth 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateGrowth:
    """calculate_growth 함수 테스트."""

    def test_yoy_and_cagr_calculated(self) -> None:
        """YoY, CAGR 3Y 모두 계산되는지 확인한다."""
        metrics = {
            "revenue": {
                "2020": Decimal("100000"),
                "2021": Decimal("120000"),
                "2022": Decimal("135000"),
                "2023": Decimal("150000"),
            },
        }
        result = calculate_growth(metrics)

        assert isinstance(result, GrowthMetrics)
        assert "revenue" in result.yoy
        assert len(result.yoy["revenue"]) == 3  # 2021, 2022, 2023
        assert "revenue" in result.cagr_3y

    def test_cagr_3y_needs_4_plus_data_points(self) -> None:
        """3년 CAGR에는 4개 이상의 데이터 포인트가 필요하다."""
        # 3개 포인트만 제공: CAGR 3Y 계산 불가
        metrics = {
            "revenue": {
                "2021": Decimal("100000"),
                "2022": Decimal("120000"),
                "2023": Decimal("135000"),
            },
        }
        result = calculate_growth(metrics)
        assert "revenue" not in result.cagr_3y

        # 4개 포인트: CAGR 3Y 계산 가능
        metrics_4 = {
            "revenue": {
                "2020": Decimal("80000"),
                "2021": Decimal("100000"),
                "2022": Decimal("120000"),
                "2023": Decimal("135000"),
            },
        }
        result_4 = calculate_growth(metrics_4)
        assert "revenue" in result_4.cagr_3y
