"""밸류에이션 계산기 테스트 (Phase D1).

> 마지막 수정: 2026-02-11 22:00:00
"""

from __future__ import annotations

from decimal import Decimal


from src.financial_engine.calculator.valuation import (
    ExitAnalysis,
    IRRScenario,
    ValuationMetrics,
    calculate_ev_ebitda,
    calculate_ev_revenue,
    calculate_exit_analysis,
    calculate_irr,
    calculate_irr_scenarios,
    calculate_moic,
    calculate_moic_scenarios,
    calculate_pe_ratio,
    calculate_valuation_metrics,
    _solve_irr,
)


# ---------------------------------------------------------------------------
# EV/EBITDA
# ---------------------------------------------------------------------------


class TestCalculateEvEbitda:
    """EV/EBITDA 멀티플 계산 테스트."""

    def test_basic_ev_ebitda(self) -> None:
        ev = {"2023": Decimal("350000"), "2024": Decimal("400000")}
        ebitda = {"2023": Decimal("35000"), "2024": Decimal("50000")}
        result = calculate_ev_ebitda(ev, ebitda)
        assert result == {"2023": 10.0, "2024": 8.0}

    def test_zero_ebitda_skipped(self) -> None:
        ev = {"2023": Decimal("350000")}
        ebitda = {"2023": Decimal("0")}
        result = calculate_ev_ebitda(ev, ebitda)
        assert result == {}

    def test_none_values_skipped(self) -> None:
        ev = {"2023": Decimal("350000"), "2024": None}
        ebitda = {"2023": None, "2024": Decimal("50000")}
        result = calculate_ev_ebitda(ev, ebitda)
        assert result == {}


# ---------------------------------------------------------------------------
# P/E Ratio
# ---------------------------------------------------------------------------


class TestCalculatePeRatio:
    """P/E Ratio 계산 테스트."""

    def test_basic_pe(self) -> None:
        eq_val = {"2023": Decimal("200000")}
        ni = {"2023": Decimal("20000")}
        result = calculate_pe_ratio(eq_val, ni)
        assert result == {"2023": 10.0}

    def test_zero_income_skipped(self) -> None:
        eq_val = {"2023": Decimal("200000")}
        ni = {"2023": Decimal("0")}
        result = calculate_pe_ratio(eq_val, ni)
        assert result == {}


# ---------------------------------------------------------------------------
# EV/Revenue
# ---------------------------------------------------------------------------


class TestCalculateEvRevenue:
    """EV/Revenue 멀티플 계산 테스트."""

    def test_basic_ev_revenue(self) -> None:
        ev = {"2023": Decimal("350000")}
        revenue = {"2023": Decimal("175000")}
        result = calculate_ev_revenue(ev, revenue)
        assert result == {"2023": 2.0}

    def test_zero_revenue_skipped(self) -> None:
        ev = {"2023": Decimal("350000")}
        revenue = {"2023": Decimal("0")}
        result = calculate_ev_revenue(ev, revenue)
        assert result == {}


# ---------------------------------------------------------------------------
# IRR 솔버
# ---------------------------------------------------------------------------


class TestSolveIrr:
    """Newton-Raphson IRR 솔버 테스트."""

    def test_simple_irr(self) -> None:
        """[-1000, 0, 0, 1331] → IRR ≈ 10% (1.10^3 = 1.331)."""
        cfs = [-1000.0, 0.0, 0.0, 1331.0]
        rate = _solve_irr(cfs)
        assert rate is not None
        assert abs(rate - 0.10) < 0.001

    def test_irr_with_annual_cash_flows(self) -> None:
        """[-1000, 100, 100, 1100] → IRR ≈ 10%."""
        cfs = [-1000.0, 100.0, 100.0, 1100.0]
        rate = _solve_irr(cfs)
        assert rate is not None
        assert abs(rate - 0.10) < 0.01

    def test_empty_cash_flows_returns_none(self) -> None:
        assert _solve_irr([]) is None

    def test_single_cash_flow_returns_none(self) -> None:
        assert _solve_irr([-1000.0]) is None


# ---------------------------------------------------------------------------
# calculate_irr
# ---------------------------------------------------------------------------


class TestCalculateIrr:
    """개별 IRR 계산 테스트."""

    def test_basic_irr_entry_exit(self) -> None:
        """100000 → 200000 (5년) → IRR ≈ 14.87%."""
        irr = calculate_irr(Decimal("100000"), Decimal("200000"), 5)
        assert irr is not None
        assert 14.0 < irr < 16.0

    def test_irr_with_cash_flows(self) -> None:
        entry = Decimal("100000")
        exit_val = Decimal("150000")
        annual = [Decimal("10000"), Decimal("10000"), Decimal("10000")]
        irr = calculate_irr(entry, exit_val, 3, annual)
        assert irr is not None
        assert irr > 0

    def test_irr_zero_entry_returns_none(self) -> None:
        assert calculate_irr(Decimal("0"), Decimal("200000"), 5) is None


# ---------------------------------------------------------------------------
# MOIC
# ---------------------------------------------------------------------------


class TestCalculateMoic:
    """MOIC 계산 테스트."""

    def test_basic_moic(self) -> None:
        result = calculate_moic(Decimal("250000"), Decimal("100000"))
        assert result == 2.5

    def test_zero_entry_returns_none(self) -> None:
        assert calculate_moic(Decimal("250000"), Decimal("0")) is None

    def test_moic_less_than_one(self) -> None:
        """손실 케이스: exit < entry → MOIC < 1."""
        result = calculate_moic(Decimal("80000"), Decimal("100000"))
        assert result is not None
        assert result == 0.8


# ---------------------------------------------------------------------------
# 시나리오 일괄 계산
# ---------------------------------------------------------------------------


class TestCalculateIrrScenarios:
    """IRR 시나리오 일괄 계산 테스트."""

    def test_three_scenarios(self) -> None:
        scenarios = {
            "base": {
                "entry_multiple": 8.0,
                "exit_multiple": 10.0,
                "holding_period": 5,
                "ebitda_at_entry": Decimal("35000"),
                "ebitda_at_exit": Decimal("50000"),
            },
            "upside": {
                "entry_multiple": 7.0,
                "exit_multiple": 12.0,
                "holding_period": 4,
                "ebitda_at_entry": Decimal("35000"),
                "ebitda_at_exit": Decimal("60000"),
            },
            "downside": {
                "entry_multiple": 9.0,
                "exit_multiple": 8.0,
                "holding_period": 5,
                "ebitda_at_entry": Decimal("35000"),
                "ebitda_at_exit": Decimal("40000"),
            },
        }
        result = calculate_irr_scenarios(scenarios)
        assert "base" in result
        assert "upside" in result
        assert isinstance(result["base"], IRRScenario)
        assert result["base"].entry_multiple == 8.0
        assert result["base"].holding_period == 5
        # Upside IRR > Base IRR
        assert result["upside"].irr > result["base"].irr

    def test_empty_scenarios_returns_empty(self) -> None:
        assert calculate_irr_scenarios({}) == {}


class TestCalculateMoicScenarios:
    """MOIC 시나리오 일괄 계산 테스트."""

    def test_basic_moic_scenarios(self) -> None:
        scenarios = {
            "base": {
                "exit_equity": Decimal("250000"),
                "entry_equity": Decimal("100000"),
            },
            "upside": {
                "exit_equity": Decimal("350000"),
                "entry_equity": Decimal("100000"),
            },
        }
        result = calculate_moic_scenarios(scenarios)
        assert result == {"base": 2.5, "upside": 3.5}


# ---------------------------------------------------------------------------
# Exit 분석
# ---------------------------------------------------------------------------


class TestCalculateExitAnalysis:
    """Exit 분석 테스트."""

    def test_exit_analysis(self) -> None:
        result = calculate_exit_analysis(
            exit_multiples=[8.0, 10.0, 12.0],
            ebitda_at_exit=Decimal("50000"),
            entry_equity=Decimal("100000"),
            holding_period=5,
        )
        assert "8.0x" in result
        assert "10.0x" in result
        assert "12.0x" in result
        assert isinstance(result["10.0x"], ExitAnalysis)
        assert result["10.0x"].exit_ev == Decimal("500000")
        assert result["10.0x"].moic == 5.0
        # 높은 멀티플 → 높은 MOIC
        assert result["12.0x"].moic > result["8.0x"].moic

    def test_exit_analysis_with_net_debt(self) -> None:
        result = calculate_exit_analysis(
            exit_multiples=[10.0],
            ebitda_at_exit=Decimal("50000"),
            entry_equity=Decimal("100000"),
            holding_period=5,
            net_debt_at_exit=Decimal("100000"),
        )
        assert "10.0x" in result
        # exit_equity = 500000 - 100000 = 400000
        assert result["10.0x"].exit_equity == Decimal("400000")
        assert result["10.0x"].moic == 4.0

    def test_exit_analysis_zero_entry(self) -> None:
        result = calculate_exit_analysis(
            exit_multiples=[10.0],
            ebitda_at_exit=Decimal("50000"),
            entry_equity=Decimal("0"),
            holding_period=5,
        )
        assert result == {}


# ---------------------------------------------------------------------------
# 통합 계산
# ---------------------------------------------------------------------------


class TestCalculateValuationMetrics:
    """통합 밸류에이션 계산 테스트."""

    def test_full_metrics(self) -> None:
        result = calculate_valuation_metrics(
            ev={"2023": Decimal("350000")},
            ebitda={"2023": Decimal("35000")},
            equity_value={"2023": Decimal("200000")},
            net_income={"2023": Decimal("20000")},
            revenue={"2023": Decimal("175000")},
            moic_scenarios_config={
                "base": {
                    "exit_equity": Decimal("250000"),
                    "entry_equity": Decimal("100000"),
                },
            },
            exit_multiples=[8.0, 10.0],
            ebitda_at_exit=Decimal("50000"),
            entry_equity=Decimal("100000"),
            holding_period=5,
        )
        assert isinstance(result, ValuationMetrics)
        assert result.ev_ebitda == {"2023": 10.0}
        assert result.pe_ratio == {"2023": 10.0}
        assert result.ev_revenue == {"2023": 2.0}
        assert result.moic_scenarios == {"base": 2.5}
        assert "8.0x" in result.exit_analysis
        assert "10.0x" in result.exit_analysis

    def test_graceful_when_ev_missing(self) -> None:
        result = calculate_valuation_metrics(
            ebitda={"2023": Decimal("35000")},
            revenue={"2023": Decimal("175000")},
        )
        assert result.ev_ebitda == {}
        assert result.ev_revenue == {}
        assert result.pe_ratio == {}

    def test_graceful_when_no_scenarios(self) -> None:
        result = calculate_valuation_metrics()
        assert result.irr_scenarios == {}
        assert result.moic_scenarios == {}
        assert result.exit_analysis == {}
