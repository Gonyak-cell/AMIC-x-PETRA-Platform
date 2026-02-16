"""수익성 지표 계산기(Profitability Calculator) 단위 테스트.

GPM, OPM, NPM, ROA, ROE 등 수익성 마진 계산을 검증합니다.

> 마지막 수정: 2026-02-09 16:28:44
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.profitability import (
    ProfitabilityMetrics,
    calculate_margin,
    calculate_profitability,
)


# ---------------------------------------------------------------------------
# calculate_margin 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateMargin:
    """calculate_margin 함수 테스트."""

    def test_basic_margin(self) -> None:
        """기본 마진 계산: 150/1000*100 = 15.0%."""
        result = calculate_margin(Decimal("150"), Decimal("1000"))
        assert result == 15.0

    def test_zero_denominator_returns_none(self) -> None:
        """분모가 0이면 None을 반환한다."""
        result = calculate_margin(Decimal("150"), Decimal("0"))
        assert result is None

    @pytest.mark.parametrize(
        "numerator, denominator",
        [
            (None, Decimal("1000")),
            (Decimal("150"), None),
            (None, None),
        ],
        ids=["분자_None", "분모_None", "둘다_None"],
    )
    def test_none_values_return_none(
        self, numerator: Decimal | None, denominator: Decimal | None
    ) -> None:
        """분자 또는 분모가 None이면 None을 반환한다."""
        assert calculate_margin(numerator, denominator) is None

    def test_negative_margin_loss_scenario(self) -> None:
        """음수 분자(적자)일 때 음수 마진을 반환한다."""
        result = calculate_margin(Decimal("-50"), Decimal("1000"))
        assert result == -5.0


# ---------------------------------------------------------------------------
# calculate_profitability 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateProfitability:
    """calculate_profitability 함수 테스트."""

    @pytest.fixture
    def two_year_data(self) -> dict:
        """2개년 테스트 데이터."""
        return {
            "revenue": {"2023": Decimal("1000"), "2024": Decimal("1200")},
            "gross_profit": {"2023": Decimal("400"), "2024": Decimal("500")},
            "operating_income": {"2023": Decimal("200"), "2024": Decimal("250")},
            "net_income": {"2023": Decimal("150"), "2024": Decimal("180")},
            "total_assets": {"2023": Decimal("5000"), "2024": Decimal("6000")},
            "total_equity": {"2023": Decimal("3000"), "2024": Decimal("3500")},
        }

    def test_all_metrics_calculated(self, two_year_data: dict) -> None:
        """GPM, OPM, NPM, ROA, ROE 모두 계산되는지 확인한다."""
        result = calculate_profitability(**two_year_data)

        assert isinstance(result, ProfitabilityMetrics)
        # GPM: 400/1000 = 40.0%, 500/1200 ≈ 41.67%
        assert result.gross_profit_margin["2023"] == pytest.approx(40.0)
        # OPM: 200/1000 = 20.0%
        assert result.operating_profit_margin["2023"] == pytest.approx(20.0)
        # NPM: 150/1000 = 15.0%
        assert result.net_profit_margin["2023"] == pytest.approx(15.0)
        # ROA: 150/5000 = 3.0%
        assert result.roa["2023"] == pytest.approx(3.0)
        # ROE: 150/3000 = 5.0%
        assert result.roe["2023"] == pytest.approx(5.0)

    def test_zero_revenue_all_margins_none(self) -> None:
        """매출이 0이면 GPM, OPM, NPM이 모두 제외된다."""
        result = calculate_profitability(
            revenue={"2023": Decimal("0")},
            gross_profit={"2023": Decimal("0")},
            operating_income={"2023": Decimal("0")},
            net_income={"2023": Decimal("0")},
            total_assets={"2023": Decimal("5000")},
            total_equity={"2023": Decimal("3000")},
        )
        assert "2023" not in result.gross_profit_margin
        assert "2023" not in result.operating_profit_margin
        assert "2023" not in result.net_profit_margin

    def test_single_year_data(self) -> None:
        """단일 연도 데이터도 정상 처리된다."""
        result = calculate_profitability(
            revenue={"2023": Decimal("1000")},
            gross_profit={"2023": Decimal("300")},
            operating_income={"2023": Decimal("100")},
            net_income={"2023": Decimal("80")},
            total_assets={"2023": Decimal("2000")},
            total_equity={"2023": Decimal("1000")},
        )
        assert result.gross_profit_margin == {"2023": pytest.approx(30.0)}
        assert result.operating_profit_margin == {"2023": pytest.approx(10.0)}
        assert result.net_profit_margin == {"2023": pytest.approx(8.0)}

    def test_missing_year_in_some_metrics(self) -> None:
        """특정 연도의 지표가 누락되면 해당 연도는 결과에서 제외된다."""
        result = calculate_profitability(
            revenue={"2023": Decimal("1000"), "2024": Decimal("1200")},
            gross_profit={"2023": Decimal("400")},  # 2024 없음
            operating_income={"2023": Decimal("200"), "2024": Decimal("250")},
            net_income={"2023": Decimal("150"), "2024": Decimal("180")},
            total_assets={"2023": Decimal("5000"), "2024": Decimal("6000")},
            total_equity={"2023": Decimal("3000"), "2024": Decimal("3500")},
        )
        # GPM: 2024는 gross_profit이 없으므로 None → 제외
        assert "2023" in result.gross_profit_margin
        assert "2024" not in result.gross_profit_margin
        # OPM: 2024도 정상 계산
        assert "2024" in result.operating_profit_margin

    def test_all_years_consistent(self, two_year_data: dict) -> None:
        """모든 연도가 일관되게 계산되는지 확인한다."""
        result = calculate_profitability(**two_year_data)
        # 두 연도 모두 존재해야 함
        for year in ["2023", "2024"]:
            assert year in result.gross_profit_margin
            assert year in result.operating_profit_margin
            assert year in result.net_profit_margin
            assert year in result.roa
            assert year in result.roe
