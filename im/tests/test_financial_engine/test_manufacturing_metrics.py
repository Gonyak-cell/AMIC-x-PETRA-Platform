"""제조업 산업별 재무 지표 계산기 단위 테스트.

OEE, 가동률, 수율, 재고회전율, CAPEX/매출 비율 계산을 검증합니다.

> 마지막 수정: 2026-02-11 15:10:00
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.manufacturing_metrics import (
    ManufacturingMetrics,
    calculate_capacity_utilization,
    calculate_capex_to_revenue,
    calculate_inventory_turnover,
    calculate_manufacturing_metrics,
    calculate_oee,
    calculate_yield_rate,
)


# ---------------------------------------------------------------------------
# calculate_oee 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateOee:
    """calculate_oee 함수 테스트."""

    def test_basic_oee_decimal_inputs(self) -> None:
        """0-1 소수 입력으로 OEE를 계산한다."""
        result = calculate_oee(
            availability={"2023": Decimal("0.90")},
            performance={"2023": Decimal("0.85")},
            quality={"2023": Decimal("0.95")},
        )
        # 0.90 * 0.85 * 0.95 * 100 = 72.675
        assert result["2023"] == pytest.approx(72.675, rel=1e-4)

    def test_oee_percentage_inputs(self) -> None:
        """0-100 백분율 입력도 올바르게 처리한다."""
        result = calculate_oee(
            availability={"2023": Decimal("90")},
            performance={"2023": Decimal("85")},
            quality={"2023": Decimal("95")},
        )
        # (90/100) * (85/100) * (95/100) * 100 = 72.675
        assert result["2023"] == pytest.approx(72.675, rel=1e-4)

    def test_any_component_none_excluded(self) -> None:
        """구성요소 중 None이 있으면 해당 연도 제외."""
        result = calculate_oee(
            availability={"2023": Decimal("0.90")},
            performance={"2023": None},
            quality={"2023": Decimal("0.95")},
        )
        assert "2023" not in result

    def test_perfect_oee(self) -> None:
        """모든 구성요소가 1(100%)이면 OEE = 100%."""
        result = calculate_oee(
            availability={"2023": Decimal("1.0")},
            performance={"2023": Decimal("1.0")},
            quality={"2023": Decimal("1.0")},
        )
        assert result["2023"] == pytest.approx(100.0)

    def test_multi_year(self) -> None:
        """여러 연도에 대해 OEE를 계산한다."""
        result = calculate_oee(
            availability={"2022": Decimal("0.88"), "2023": Decimal("0.92")},
            performance={"2022": Decimal("0.82"), "2023": Decimal("0.87")},
            quality={"2022": Decimal("0.93"), "2023": Decimal("0.96")},
        )
        assert len(result) == 2
        assert "2022" in result
        assert "2023" in result


# ---------------------------------------------------------------------------
# calculate_capacity_utilization 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateCapacityUtilization:
    """calculate_capacity_utilization 함수 테스트."""

    def test_basic_utilization(self) -> None:
        """가동률 = 실제 / 최대 × 100."""
        result = calculate_capacity_utilization(
            actual_output={"2023": Decimal("850")},
            max_capacity={"2023": Decimal("1000")},
        )
        assert result["2023"] == pytest.approx(85.0)

    def test_zero_max_capacity_excluded(self) -> None:
        """최대 CAPA가 0이면 제외."""
        result = calculate_capacity_utilization(
            actual_output={"2023": Decimal("850")},
            max_capacity={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_excluded(self) -> None:
        """None 값은 제외."""
        result = calculate_capacity_utilization(
            actual_output={"2023": None},
            max_capacity={"2023": Decimal("1000")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_yield_rate 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateYieldRate:
    """calculate_yield_rate 함수 테스트."""

    def test_basic_yield(self) -> None:
        """수율 = 양품 / 총생산 × 100."""
        result = calculate_yield_rate(
            good_units={"2023": Decimal("950")},
            total_units={"2023": Decimal("1000")},
        )
        assert result["2023"] == pytest.approx(95.0)

    def test_zero_total_excluded(self) -> None:
        """총 생산이 0이면 제외."""
        result = calculate_yield_rate(
            good_units={"2023": Decimal("0")},
            total_units={"2023": Decimal("0")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_inventory_turnover 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateInventoryTurnover:
    """calculate_inventory_turnover 함수 테스트."""

    def test_basic_turnover(self) -> None:
        """재고회전율 = COGS / 평균재고."""
        result = calculate_inventory_turnover(
            cogs={"2023": Decimal("600000")},
            avg_inventory={"2023": Decimal("100000")},
        )
        assert result["2023"] == pytest.approx(6.0)

    def test_zero_inventory_excluded(self) -> None:
        """평균재고가 0이면 제외."""
        result = calculate_inventory_turnover(
            cogs={"2023": Decimal("600000")},
            avg_inventory={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_cogs_excluded(self) -> None:
        """COGS가 None이면 제외."""
        result = calculate_inventory_turnover(
            cogs={"2023": None},
            avg_inventory={"2023": Decimal("100000")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_capex_to_revenue 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateCapexToRevenue:
    """calculate_capex_to_revenue 함수 테스트."""

    def test_basic_ratio(self) -> None:
        """CAPEX/매출 = |CAPEX| / 매출 × 100."""
        result = calculate_capex_to_revenue(
            capex={"2023": Decimal("50000")},
            revenue={"2023": Decimal("500000")},
        )
        assert result["2023"] == pytest.approx(10.0)

    def test_negative_capex_abs(self) -> None:
        """음수 CAPEX(CF 관례)도 절대값으로 처리."""
        result = calculate_capex_to_revenue(
            capex={"2023": Decimal("-50000")},
            revenue={"2023": Decimal("500000")},
        )
        assert result["2023"] == pytest.approx(10.0)

    def test_zero_revenue_excluded(self) -> None:
        """매출이 0이면 제외."""
        result = calculate_capex_to_revenue(
            capex={"2023": Decimal("50000")},
            revenue={"2023": Decimal("0")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_manufacturing_metrics 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateManufacturingMetrics:
    """calculate_manufacturing_metrics 통합 테스트."""

    @pytest.fixture
    def full_data(self) -> dict:
        """전체 제조업 테스트 데이터."""
        return {
            "revenue": {"2023": Decimal("1000000")},
            "cogs": {"2023": Decimal("600000")},
            "capex": {"2023": Decimal("-80000")},
            "avg_inventory": {"2023": Decimal("100000")},
            "availability": {"2023": Decimal("0.92")},
            "performance": {"2023": Decimal("0.88")},
            "quality": {"2023": Decimal("0.96")},
            "actual_output": {"2023": Decimal("880")},
            "max_capacity": {"2023": Decimal("1000")},
            "good_units": {"2023": Decimal("960")},
            "total_units": {"2023": Decimal("1000")},
        }

    def test_all_metrics_calculated(self, full_data: dict) -> None:
        """모든 입력 제공 시 5개 지표 모두 계산된다."""
        result = calculate_manufacturing_metrics(**full_data)

        assert isinstance(result, ManufacturingMetrics)
        assert len(result.oee) == 1
        assert len(result.capacity_utilization) == 1
        assert len(result.yield_rate) == 1
        assert len(result.inventory_turnover) == 1
        assert len(result.capex_to_revenue) == 1

    def test_minimal_data(self) -> None:
        """필수 입력만 제공 시 재고회전율과 CAPEX/매출만 계산."""
        result = calculate_manufacturing_metrics(
            revenue={"2023": Decimal("1000000")},
            cogs={"2023": Decimal("600000")},
            capex={"2023": Decimal("80000")},
        )
        assert result.oee == {}
        assert result.capacity_utilization == {}
        assert result.yield_rate == {}
        assert result.capex_to_revenue["2023"] == pytest.approx(8.0)

    def test_dataclass_is_frozen(self, full_data: dict) -> None:
        """ManufacturingMetrics는 frozen 데이터클래스이다."""
        result = calculate_manufacturing_metrics(**full_data)
        with pytest.raises(AttributeError):
            result.oee = {}  # type: ignore[misc]

    def test_inventory_turnover_from_standard_accounts(self) -> None:
        """COGS와 재고자산을 이용한 재고회전율 계산."""
        result = calculate_manufacturing_metrics(
            revenue={"2023": Decimal("1000000")},
            cogs={"2023": Decimal("720000")},
            capex={"2023": Decimal("0")},
            avg_inventory={"2023": Decimal("120000")},
        )
        # 720000 / 120000 = 6.0
        assert result.inventory_turnover["2023"] == pytest.approx(6.0)
