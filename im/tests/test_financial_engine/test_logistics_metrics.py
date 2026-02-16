"""물류/운송 산업별 재무 지표 계산기 단위 테스트.

정시 배송률, 플릿 가동률, 톤km당 매출, 건당 비용 계산을 검증합니다.

> 마지막 수정: 2026-02-11 15:20:00
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.calculator.logistics_metrics import (
    LogisticsMetrics,
    calculate_cost_per_delivery,
    calculate_fleet_utilization,
    calculate_logistics_metrics,
    calculate_on_time_delivery,
    calculate_revenue_per_tonkm,
)


# ---------------------------------------------------------------------------
# calculate_on_time_delivery 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateOnTimeDelivery:
    """calculate_on_time_delivery 함수 테스트."""

    def test_basic_otd(self) -> None:
        """정시 배송률 = 정시건수 / 총건수 × 100."""
        result = calculate_on_time_delivery(
            on_time_count={"2023": Decimal("950")},
            total_deliveries={"2023": Decimal("1000")},
        )
        assert result["2023"] == pytest.approx(95.0)

    def test_perfect_otd(self) -> None:
        """100% 정시 배송."""
        result = calculate_on_time_delivery(
            on_time_count={"2023": Decimal("1000")},
            total_deliveries={"2023": Decimal("1000")},
        )
        assert result["2023"] == pytest.approx(100.0)

    def test_zero_deliveries_excluded(self) -> None:
        """총 배송 건수 0이면 제외."""
        result = calculate_on_time_delivery(
            on_time_count={"2023": Decimal("0")},
            total_deliveries={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_excluded(self) -> None:
        """None 값 제외."""
        result = calculate_on_time_delivery(
            on_time_count={"2023": None},
            total_deliveries={"2023": Decimal("1000")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_fleet_utilization 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateFleetUtilization:
    """calculate_fleet_utilization 함수 테스트."""

    def test_basic_utilization(self) -> None:
        """플릿 가동률 = 가동 / 보유 × 100."""
        result = calculate_fleet_utilization(
            active_fleet={"2023": Decimal("80")},
            total_fleet={"2023": Decimal("100")},
        )
        assert result["2023"] == pytest.approx(80.0)

    def test_zero_fleet_excluded(self) -> None:
        """보유 차량 0이면 제외."""
        result = calculate_fleet_utilization(
            active_fleet={"2023": Decimal("0")},
            total_fleet={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_excluded(self) -> None:
        """None 값 제외."""
        result = calculate_fleet_utilization(
            active_fleet={"2023": Decimal("80")},
            total_fleet={"2023": None},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_revenue_per_tonkm 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateRevenuePerTonkm:
    """calculate_revenue_per_tonkm 함수 테스트."""

    def test_basic_revenue_per_tonkm(self) -> None:
        """톤km당 매출 = 운송매출 / 총톤km."""
        result = calculate_revenue_per_tonkm(
            transport_revenue={"2023": Decimal("500000")},
            total_tonkm={"2023": Decimal("100000")},
        )
        assert result["2023"] == Decimal("5")

    def test_zero_tonkm_excluded(self) -> None:
        """총 톤km 0이면 제외."""
        result = calculate_revenue_per_tonkm(
            transport_revenue={"2023": Decimal("500000")},
            total_tonkm={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_multi_year(self) -> None:
        """여러 연도에 대해 계산."""
        result = calculate_revenue_per_tonkm(
            transport_revenue={
                "2022": Decimal("400000"),
                "2023": Decimal("500000"),
            },
            total_tonkm={
                "2022": Decimal("80000"),
                "2023": Decimal("100000"),
            },
        )
        assert len(result) == 2
        assert result["2022"] == Decimal("5")
        assert result["2023"] == Decimal("5")


# ---------------------------------------------------------------------------
# calculate_cost_per_delivery 단위 테스트
# ---------------------------------------------------------------------------


class TestCalculateCostPerDelivery:
    """calculate_cost_per_delivery 함수 테스트."""

    def test_basic_cost(self) -> None:
        """건당 비용 = 운영비 / 총건수."""
        result = calculate_cost_per_delivery(
            operating_cost={"2023": Decimal("800000")},
            total_deliveries={"2023": Decimal("10000")},
        )
        assert result["2023"] == Decimal("80")

    def test_zero_deliveries_excluded(self) -> None:
        """총 배송 건수 0이면 제외."""
        result = calculate_cost_per_delivery(
            operating_cost={"2023": Decimal("800000")},
            total_deliveries={"2023": Decimal("0")},
        )
        assert "2023" not in result

    def test_none_excluded(self) -> None:
        """None 값 제외."""
        result = calculate_cost_per_delivery(
            operating_cost={"2023": None},
            total_deliveries={"2023": Decimal("10000")},
        )
        assert "2023" not in result


# ---------------------------------------------------------------------------
# calculate_logistics_metrics 통합 테스트
# ---------------------------------------------------------------------------


class TestCalculateLogisticsMetrics:
    """calculate_logistics_metrics 통합 테스트."""

    @pytest.fixture
    def full_data(self) -> dict:
        """전체 물류 테스트 데이터."""
        return {
            "revenue": {"2023": Decimal("1000000")},
            "on_time_count": {"2023": Decimal("9500")},
            "total_deliveries": {"2023": Decimal("10000")},
            "active_fleet": {"2023": Decimal("85")},
            "total_fleet": {"2023": Decimal("100")},
            "transport_revenue": {"2023": Decimal("800000")},
            "total_tonkm": {"2023": Decimal("200000")},
            "operating_cost": {"2023": Decimal("700000")},
        }

    def test_all_metrics_calculated(self, full_data: dict) -> None:
        """모든 입력 제공 시 4개 지표 모두 계산된다."""
        result = calculate_logistics_metrics(**full_data)

        assert isinstance(result, LogisticsMetrics)
        assert result.on_time_delivery["2023"] == pytest.approx(95.0)
        assert result.fleet_utilization["2023"] == pytest.approx(85.0)
        assert result.revenue_per_tonkm["2023"] == Decimal("4")
        assert result.cost_per_delivery["2023"] == Decimal("70")

    def test_minimal_data(self) -> None:
        """revenue만 제공 시 모든 지표 빈 dict."""
        result = calculate_logistics_metrics(
            revenue={"2023": Decimal("1000000")},
        )
        assert result.on_time_delivery == {}
        assert result.fleet_utilization == {}
        assert result.revenue_per_tonkm == {}
        assert result.cost_per_delivery == {}

    def test_dataclass_is_frozen(self, full_data: dict) -> None:
        """LogisticsMetrics는 frozen 데이터클래스이다."""
        result = calculate_logistics_metrics(**full_data)
        with pytest.raises(AttributeError):
            result.on_time_delivery = {}  # type: ignore[misc]

    def test_partial_inputs(self) -> None:
        """일부 입력만 제공."""
        result = calculate_logistics_metrics(
            revenue={"2023": Decimal("1000000")},
            on_time_count={"2023": Decimal("9800")},
            total_deliveries={"2023": Decimal("10000")},
        )
        assert result.on_time_delivery["2023"] == pytest.approx(98.0)
        assert result.fleet_utilization == {}
        assert result.revenue_per_tonkm == {}
        assert result.cost_per_delivery == {}

    def test_cost_per_delivery_uses_total_deliveries(self) -> None:
        """건당 비용과 정시 배송률이 같은 total_deliveries를 공유."""
        result = calculate_logistics_metrics(
            revenue={"2023": Decimal("1000000")},
            on_time_count={"2023": Decimal("900")},
            total_deliveries={"2023": Decimal("1000")},
            operating_cost={"2023": Decimal("50000")},
        )
        assert result.on_time_delivery["2023"] == pytest.approx(90.0)
        assert result.cost_per_delivery["2023"] == Decimal("50")
