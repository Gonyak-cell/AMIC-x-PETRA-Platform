"""헬스케어/바이오 산업별 재무 지표 계산기 단위 테스트.

rNPV, 단계별 성공률, 특허 잔여기간, R&D/매출 계산을 검증합니다.

> 마지막 수정: 2026-02-11 15:20:00
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.healthcare_metrics import (
    HealthcareMetrics,
    calculate_healthcare_metrics,
    calculate_patent_remaining,
    calculate_phase_success_rates,
    calculate_rd_to_revenue,
    calculate_rnpv,
)


# ---------------------------------------------------------------------------
# calculate_rnpv 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateRnpv:
    """calculate_rnpv 함수 테스트."""

    def test_basic_rnpv(self) -> None:
        """기본 rNPV 계산: CF × P / (1+r)^t."""
        result = calculate_rnpv(
            expected_cash_flows={"1": Decimal("1000"), "2": Decimal("2000")},
            success_probabilities={"1": Decimal("0.80"), "2": Decimal("0.60")},
            discount_rate=Decimal("0.10"),
        )
        # t=1: 1000 * 0.80 / 1.10 = 727.27...
        assert float(result["1"]) == pytest.approx(727.27, rel=1e-2)
        # t=2: 2000 * 0.60 / 1.21 = 991.74...
        assert float(result["2"]) == pytest.approx(991.74, rel=1e-2)

    def test_negative_discount_rate_empty(self) -> None:
        """할인율이 음수이면 빈 결과."""
        result = calculate_rnpv(
            expected_cash_flows={"1": Decimal("1000")},
            success_probabilities={"1": Decimal("0.80")},
            discount_rate=Decimal("-0.05"),
        )
        assert result == {}

    def test_none_cf_excluded(self) -> None:
        """현금흐름이 None인 단계 제외."""
        result = calculate_rnpv(
            expected_cash_flows={"1": Decimal("1000"), "2": None},
            success_probabilities={"1": Decimal("0.80"), "2": Decimal("0.60")},
            discount_rate=Decimal("0.10"),
        )
        assert "1" in result
        assert "2" not in result

    def test_zero_period_no_discounting(self) -> None:
        """t=0이면 할인 없음."""
        result = calculate_rnpv(
            expected_cash_flows={"0": Decimal("1000")},
            success_probabilities={"0": Decimal("0.50")},
            discount_rate=Decimal("0.10"),
        )
        # 1000 * 0.50 / 1.10^0 = 500
        assert result["0"] == Decimal("500")


# ---------------------------------------------------------------------------
# calculate_phase_success_rates 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculatePhaseSuccessRates:
    """calculate_phase_success_rates 함수 테스트."""

    def test_basic_conversion(self) -> None:
        """Decimal → float 변환."""
        result = calculate_phase_success_rates(
            phase_data={
                "Phase I": Decimal("0.65"),
                "Phase II": Decimal("0.35"),
                "Phase III": Decimal("0.58"),
            },
        )
        assert result["Phase I"] == pytest.approx(0.65)
        assert result["Phase II"] == pytest.approx(0.35)
        assert result["Phase III"] == pytest.approx(0.58)

    def test_none_excluded(self) -> None:
        """None인 단계는 제외."""
        result = calculate_phase_success_rates(
            phase_data={"Phase I": Decimal("0.65"), "Phase II": None},
        )
        assert "Phase I" in result
        assert "Phase II" not in result

    def test_empty_input(self) -> None:
        """빈 입력 → 빈 결과."""
        result = calculate_phase_success_rates(phase_data={})
        assert result == {}


# ---------------------------------------------------------------------------
# calculate_patent_remaining 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculatePatentRemaining:
    """calculate_patent_remaining 함수 테스트."""

    def test_basic_remaining(self) -> None:
        """잔여기간 = 만료연도 - 현재연도."""
        result = calculate_patent_remaining(
            patent_expiry_years={"DrugA": Decimal("2030"), "DrugB": Decimal("2028")},
            current_year=2026,
        )
        assert result["DrugA"] == pytest.approx(4.0)
        assert result["DrugB"] == pytest.approx(2.0)

    def test_expired_patent_excluded(self) -> None:
        """만료된 특허(음수)는 제외."""
        result = calculate_patent_remaining(
            patent_expiry_years={"DrugA": Decimal("2024")},
            current_year=2026,
        )
        assert "DrugA" not in result

    def test_none_excluded(self) -> None:
        """None인 항목은 제외."""
        result = calculate_patent_remaining(
            patent_expiry_years={"DrugA": None},
            current_year=2026,
        )
        assert "DrugA" not in result

    def test_exact_expiry_year_included(self) -> None:
        """만료연도 = 현재연도이면 잔여 0년 (포함)."""
        result = calculate_patent_remaining(
            patent_expiry_years={"DrugA": Decimal("2026")},
            current_year=2026,
        )
        assert result["DrugA"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_rd_to_revenue 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateRdToRevenue:
    """calculate_rd_to_revenue 함수 테스트."""

    def test_basic_ratio(self) -> None:
        """R&D/매출 = R&D비 / 매출 × 100."""
        result = calculate_rd_to_revenue(
            rd_expense={"2023": Decimal("50000")},
            revenue={"2023": Decimal("200000")},
        )
        assert result["2023"] == pytest.approx(25.0)

    def test_zero_revenue_excluded(self) -> None:
        """매출 0이면 제외 (pre-revenue 바이오텍)."""
        result = calculate_rd_to_revenue(
            rd_expense={"2023": Decimal("50000")},
            revenue={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_rd_excluded(self) -> None:
        """R&D비가 None이면 제외."""
        result = calculate_rd_to_revenue(
            rd_expense={"2023": None},
            revenue={"2023": Decimal("200000")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_healthcare_metrics 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateHealthcareMetrics:
    """calculate_healthcare_metrics 통합 테스트."""

    @pytest.fixture
    def full_data(self) -> dict:
        """전체 헬스케어 테스트 데이터."""
        return {
            "revenue": {"2023": Decimal("500000"), "2024": Decimal("600000")},
            "rd_expense": {"2023": Decimal("150000"), "2024": Decimal("180000")},
            "expected_cash_flows": {"1": Decimal("1000"), "2": Decimal("3000")},
            "success_probabilities": {"1": Decimal("0.65"), "2": Decimal("0.35")},
            "discount_rate": Decimal("0.10"),
            "phase_data": {
                "Phase I": Decimal("0.65"),
                "Phase II": Decimal("0.35"),
                "Phase III": Decimal("0.58"),
            },
            "patent_expiry_years": {
                "DrugA": Decimal("2030"),
                "DrugB": Decimal("2028"),
            },
            "current_year": 2026,
        }

    def test_all_metrics_calculated(self, full_data: dict) -> None:
        """모든 입력 제공 시 4개 지표 모두 계산된다."""
        result = calculate_healthcare_metrics(**full_data)

        assert isinstance(result, HealthcareMetrics)
        assert len(result.rnpv) == 2
        assert len(result.phase_success_rates) == 3
        assert len(result.patent_remaining_years) == 2
        assert len(result.rd_to_revenue) == 2

    def test_minimal_data(self) -> None:
        """revenue만 제공 시 모든 지표 빈 dict."""
        result = calculate_healthcare_metrics(
            revenue={"2023": Decimal("500000")},
        )
        assert result.rnpv == {}
        assert result.phase_success_rates == {}
        assert result.patent_remaining_years == {}
        assert result.rd_to_revenue == {}

    def test_dataclass_is_frozen(self, full_data: dict) -> None:
        """HealthcareMetrics는 frozen 데이터클래스이다."""
        result = calculate_healthcare_metrics(**full_data)
        with pytest.raises(AttributeError):
            result.rnpv = {}  # type: ignore[misc]

    def test_rd_to_revenue_values(self, full_data: dict) -> None:
        """R&D/매출 값이 정확히 계산되는지 확인."""
        result = calculate_healthcare_metrics(**full_data)
        # 2023: 150000/500000*100 = 30.0
        assert result.rd_to_revenue["2023"] == pytest.approx(30.0)

    def test_partial_inputs(self) -> None:
        """일부 선택 입력만 제공."""
        result = calculate_healthcare_metrics(
            revenue={"2023": Decimal("500000")},
            rd_expense={"2023": Decimal("100000")},
            phase_data={"Phase I": Decimal("0.65")},
        )
        assert result.rd_to_revenue["2023"] == pytest.approx(20.0)
        assert result.phase_success_rates["Phase I"] == pytest.approx(0.65)
        assert result.rnpv == {}
        assert result.patent_remaining_years == {}
