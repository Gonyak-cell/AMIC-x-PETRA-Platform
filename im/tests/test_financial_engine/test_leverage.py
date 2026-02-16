"""레버리지 지표 계산기(Leverage Calculator) 단위 테스트.

D/E Ratio, ICR, Net Debt/EBITDA 계산을 검증합니다.

> 마지막 수정: 2026-02-09 16:28:44
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.leverage import (
    LeverageMetrics,
    calculate_debt_to_equity,
    calculate_interest_coverage,
    calculate_leverage,
)


# ---------------------------------------------------------------------------
# calculate_debt_to_equity 테스트
# ---------------------------------------------------------------------------


class TestCalculateDebtToEquity:
    """calculate_debt_to_equity 함수 테스트."""

    def test_basic_de_ratio(self) -> None:
        """기본 D/E: 500/1000 = 0.5."""
        result = calculate_debt_to_equity(
            total_liabilities={"2023": Decimal("500")},
            total_equity={"2023": Decimal("1000")},
        )
        assert result == {"2023": pytest.approx(0.5)}

    def test_zero_equity_skipped(self) -> None:
        """자기자본이 0이면 해당 연도를 건너뛴다."""
        result = calculate_debt_to_equity(
            total_liabilities={"2023": Decimal("500")},
            total_equity={"2023": Decimal("0")},
        )
        assert result == {}

    def test_negative_equity(self) -> None:
        """자기자본이 음수여도 계산을 수행한다 (결과가 음수)."""
        result = calculate_debt_to_equity(
            total_liabilities={"2023": Decimal("500")},
            total_equity={"2023": Decimal("-200")},
        )
        assert result["2023"] == pytest.approx(-2.5)


# ---------------------------------------------------------------------------
# calculate_interest_coverage 테스트
# ---------------------------------------------------------------------------


class TestCalculateInterestCoverage:
    """calculate_interest_coverage 함수 테스트."""

    def test_basic_icr(self) -> None:
        """기본 ICR: 300/100 = 3.0."""
        result = calculate_interest_coverage(
            operating_income={"2023": Decimal("300")},
            interest_expense={"2023": Decimal("100")},
        )
        assert result == {"2023": pytest.approx(3.0)}

    def test_zero_interest_skipped(self) -> None:
        """이자비용이 0이면 해당 연도를 건너뛴다."""
        result = calculate_interest_coverage(
            operating_income={"2023": Decimal("300")},
            interest_expense={"2023": Decimal("0")},
        )
        assert result == {}


# ---------------------------------------------------------------------------
# calculate_leverage 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateLeverage:
    """calculate_leverage 함수 테스트."""

    def test_all_three_metrics(self) -> None:
        """D/E, ICR, Net Debt/EBITDA 세 지표가 모두 계산되는지 확인한다."""
        result = calculate_leverage(
            total_liabilities={"2023": Decimal("500")},
            total_equity={"2023": Decimal("1000")},
            operating_income={"2023": Decimal("300")},
            interest_expense={"2023": Decimal("100")},
            total_debt={"2023": Decimal("400")},
            cash_and_equivalents={"2023": Decimal("100")},
            ebitda={"2023": Decimal("300")},
        )
        assert isinstance(result, LeverageMetrics)
        assert result.debt_to_equity == {"2023": pytest.approx(0.5)}
        assert result.interest_coverage == {"2023": pytest.approx(3.0)}
        # Net Debt = 400 - 100 = 300, Net Debt/EBITDA = 300/300 = 1.0
        assert result.net_debt_to_ebitda == {"2023": pytest.approx(1.0)}

    def test_net_debt_ebitda_when_all_provided(self) -> None:
        """Net Debt/EBITDA: total_debt, cash, ebitda 모두 제공 시 계산."""
        result = calculate_leverage(
            total_liabilities={"2023": Decimal("500")},
            total_equity={"2023": Decimal("1000")},
            operating_income={"2023": Decimal("200")},
            interest_expense={"2023": Decimal("50")},
            total_debt={"2023": Decimal("600")},
            cash_and_equivalents={"2023": Decimal("200")},
            ebitda={"2023": Decimal("400")},
        )
        # Net Debt = 600 - 200 = 400, Net Debt/EBITDA = 400/400 = 1.0
        assert result.net_debt_to_ebitda["2023"] == pytest.approx(1.0)

    def test_net_debt_ebitda_empty_when_components_missing(self) -> None:
        """Net Debt/EBITDA: 구성 요소가 하나라도 None이면 빈 딕셔너리."""
        result = calculate_leverage(
            total_liabilities={"2023": Decimal("500")},
            total_equity={"2023": Decimal("1000")},
            operating_income={"2023": Decimal("200")},
            interest_expense={"2023": Decimal("50")},
            # total_debt, cash_and_equivalents, ebitda 미제공
        )
        assert result.net_debt_to_ebitda == {}
