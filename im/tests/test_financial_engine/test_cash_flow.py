"""현금흐름 지표 계산기(Cash Flow Calculator) 단위 테스트.

EBITDA, FCF, NWC, EBITDA Margin 계산을 검증합니다.

> 마지막 수정: 2026-02-09 16:28:44
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.cash_flow import (
    CashFlowMetrics,
    calculate_cash_flow_metrics,
    calculate_ebitda,
    calculate_fcf,
    calculate_nwc,
)


# ---------------------------------------------------------------------------
# calculate_ebitda 테스트
# ---------------------------------------------------------------------------


class TestCalculateEBITDA:
    """calculate_ebitda 함수 테스트."""

    def test_basic_ebitda(self) -> None:
        """기본 EBITDA: 영업이익 + 감가상각비 = EBITDA."""
        oi = {"2023": Decimal("500")}
        dep = {"2023": Decimal("100")}
        result = calculate_ebitda(oi, dep)
        assert result == {"2023": Decimal("600")}

    def test_ebitda_with_amortization(self) -> None:
        """상각비 포함 EBITDA: OI + Dep + Amort."""
        oi = {"2023": Decimal("500")}
        dep = {"2023": Decimal("100")}
        amort = {"2023": Decimal("50")}
        result = calculate_ebitda(oi, dep, amort)
        assert result == {"2023": Decimal("650")}

    def test_ebitda_none_values_skipped(self) -> None:
        """영업이익 또는 감가상각비가 None인 연도는 건너뛴다."""
        oi = {"2022": None, "2023": Decimal("500")}
        dep = {"2022": Decimal("100"), "2023": Decimal("100")}
        result = calculate_ebitda(oi, dep)
        assert "2022" not in result
        assert result["2023"] == Decimal("600")

    def test_ebitda_amortization_none_year_skipped(self) -> None:
        """amortization 딕셔너리가 제공되었으나 해당 연도 값이 None이면 건너뛴다."""
        oi = {"2022": Decimal("500"), "2023": Decimal("600")}
        dep = {"2022": Decimal("100"), "2023": Decimal("120")}
        amort = {"2022": Decimal("50"), "2023": None}
        result = calculate_ebitda(oi, dep, amort)
        assert result == {"2022": Decimal("650")}
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_fcf 테스트
# ---------------------------------------------------------------------------


class TestCalculateFCF:
    """calculate_fcf 함수 테스트."""

    def test_basic_fcf(self) -> None:
        """기본 FCF: OCF - |CapEx|."""
        ocf = {"2023": Decimal("800")}
        capex = {"2023": Decimal("200")}
        result = calculate_fcf(ocf, capex)
        assert result == {"2023": Decimal("600")}

    def test_fcf_negative_capex_absolute_value(self) -> None:
        """음수 CapEx도 절대값으로 처리한다."""
        ocf = {"2023": Decimal("800")}
        capex = {"2023": Decimal("-200")}
        result = calculate_fcf(ocf, capex)
        # FCF = 800 - |-200| = 800 - 200 = 600
        assert result == {"2023": Decimal("600")}


# ---------------------------------------------------------------------------
# calculate_nwc 테스트
# ---------------------------------------------------------------------------


class TestCalculateNWC:
    """calculate_nwc 함수 테스트."""

    def test_basic_nwc(self) -> None:
        """기본 NWC: 유동자산 - 유동부채."""
        ca = {"2023": Decimal("3000")}
        cl = {"2023": Decimal("1500")}
        result = calculate_nwc(ca, cl)
        assert result == {"2023": Decimal("1500")}


# ---------------------------------------------------------------------------
# calculate_cash_flow_metrics 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateCashFlowMetrics:
    """calculate_cash_flow_metrics 함수 테스트."""

    def test_all_metrics_together(self) -> None:
        """모든 지표가 함께 계산되는지 확인한다."""
        result = calculate_cash_flow_metrics(
            operating_income={"2023": Decimal("600")},
            depreciation={"2023": Decimal("120")},
            operating_cash_flow={"2023": Decimal("800")},
            capex={"2023": Decimal("200")},
            current_assets={"2023": Decimal("3000")},
            current_liabilities={"2023": Decimal("1500")},
            revenue={"2023": Decimal("2000")},
        )
        assert isinstance(result, CashFlowMetrics)
        assert result.ebitda == {"2023": Decimal("720")}
        assert result.free_cash_flow == {"2023": Decimal("600")}
        assert result.net_working_capital == {"2023": Decimal("1500")}
        # EBITDA Margin = 720 / 2000 * 100 = 36.0%
        assert result.ebitda_margin["2023"] == pytest.approx(36.0)

    def test_ebitda_margin_calculation(self) -> None:
        """EBITDA 마진: EBITDA / Revenue * 100."""
        result = calculate_cash_flow_metrics(
            operating_income={"2023": Decimal("500")},
            depreciation={"2023": Decimal("100")},
            revenue={"2023": Decimal("1000")},
        )
        # EBITDA = 600, Margin = 600/1000*100 = 60.0%
        assert result.ebitda_margin["2023"] == pytest.approx(60.0)

    def test_optional_params_empty_when_not_provided(self) -> None:
        """FCF/NWC 입력이 없으면 빈 딕셔너리를 반환한다."""
        result = calculate_cash_flow_metrics(
            operating_income={"2023": Decimal("500")},
            depreciation={"2023": Decimal("100")},
        )
        assert result.free_cash_flow == {}
        assert result.net_working_capital == {}
        assert result.ebitda_margin == {}

    def test_missing_year_handling(self) -> None:
        """연도가 누락된 경우 해당 연도는 결과에서 제외된다."""
        result = calculate_cash_flow_metrics(
            operating_income={"2022": Decimal("400"), "2023": Decimal("500")},
            depreciation={"2023": Decimal("100")},  # 2022 없음
        )
        # 2022: dep가 None → 건너뜀
        assert "2022" not in result.ebitda
        assert result.ebitda == {"2023": Decimal("600")}
