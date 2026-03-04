"""매출 Deep-dive 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from app.engines.revenue_engine import (
    RevenueBreakdownResult,
    _compute_hhi,
    compute_monthly_trend,
    compute_revenue_breakdown,
)

# ── Helpers ──────────────────────────────────────────────


def _entry(
    customer: str = "",
    product: str = "",
    amount: str = "0",
    period: str = "FY2024",
    month: str = "",
) -> dict:
    return {
        "customer_name": customer,
        "product_name": product,
        "amount": amount,
        "period": period,
        "month": month,
    }


# ── HHI ──────────────────────────────────────────────────


class TestComputeHHI:
    def test_monopoly(self):
        """단일 항목 100% → HHI = 10000."""
        hhi = _compute_hhi({"A": Decimal("100")}, Decimal("100"))
        assert hhi == Decimal("10000.00")

    def test_equal_split_two(self):
        """2개 항목 50:50 → HHI = 5000."""
        hhi = _compute_hhi({"A": Decimal("50"), "B": Decimal("50")}, Decimal("100"))
        assert hhi == Decimal("5000.00")

    def test_fragmented(self):
        """10개 항목 균등 → HHI = 1000."""
        items = {f"item_{i}": Decimal("10") for i in range(10)}
        hhi = _compute_hhi(items, Decimal("100"))
        assert hhi == Decimal("1000.00")

    def test_zero_revenue(self):
        hhi = _compute_hhi({"A": Decimal("100")}, Decimal("0"))
        assert hhi == Decimal("0")


# ── Revenue Breakdown ─────────────────────────────────────


class TestComputeRevenueBreakdown:
    def test_basic_customer_breakdown(self):
        entries = [
            _entry(customer="A사", amount="50000", period="FY2024"),
            _entry(customer="B사", amount="30000", period="FY2024"),
            _entry(customer="C사", amount="20000", period="FY2024"),
        ]
        result, evidence = compute_revenue_breakdown(
            entries,
            dimension="customer",
            dimension_key="customer_name",
        )

        assert result.dimension == "customer"
        assert result.total_revenue == Decimal(
            "100000.0000"
        )  # sum of all items in latest period
        assert len(result.breakdown) == 3
        assert result.breakdown[0].name == "A사"
        assert result.breakdown[0].rank == 1
        assert result.breakdown[0].share_pct == Decimal("50.00")

        # Evidence generated
        assert len(evidence) == 3

    def test_top_n_with_others(self):
        entries = [
            _entry(customer="A사", amount="50000"),
            _entry(customer="B사", amount="30000"),
            _entry(customer="C사", amount="10000"),
            _entry(customer="D사", amount="5000"),
            _entry(customer="E사", amount="3000"),
            _entry(customer="F사", amount="2000"),
        ]
        result, _ = compute_revenue_breakdown(
            entries,
            dimension="customer",
            dimension_key="customer_name",
            top_n=3,
        )

        assert len(result.breakdown) == 4  # Top 3 + Others
        assert result.breakdown[3].name == "기타 (Others)"
        assert result.top_n_count == 3

    def test_concentration_warning(self):
        entries = [
            _entry(customer="독점사", amount="95000"),
            _entry(customer="기타", amount="5000"),
        ]
        result, _ = compute_revenue_breakdown(
            entries,
            dimension="customer",
            dimension_key="customer_name",
        )

        assert result.concentration_index > Decimal("2500")
        assert any("HIGH_CONCENTRATION" in w for w in result.warnings)

    def test_empty_entries(self):
        result, _ = compute_revenue_breakdown(
            [],
            dimension="customer",
            dimension_key="customer_name",
        )
        assert result.total_revenue == Decimal("0")
        assert len(result.warnings) > 0

    def test_multi_period_yoy(self):
        entries = [
            _entry(customer="A사", amount="100000", period="FY2023"),
            _entry(customer="A사", amount="120000", period="FY2024"),
        ]
        result, _ = compute_revenue_breakdown(
            entries,
            dimension="customer",
            dimension_key="customer_name",
        )

        a_item = result.breakdown[0]
        assert a_item.yoy_pct is not None
        assert a_item.yoy_pct == Decimal("20.00")

    def test_product_dimension(self):
        entries = [
            _entry(product="제품A", amount="60000"),
            _entry(product="제품B", amount="40000"),
        ]
        result, _ = compute_revenue_breakdown(
            entries,
            dimension="product",
            dimension_key="product_name",
        )
        assert result.dimension == "product"
        assert len(result.breakdown) == 2


# ── Monthly Trend ─────────────────────────────────────────


class TestComputeMonthlyTrend:
    def test_basic_trend(self):
        entries = [
            {"month": "2024-01", "amount": "10000"},
            {"month": "2024-02", "amount": "12000"},
            {"month": "2024-03", "amount": "8000"},
        ]
        result, evidence = compute_monthly_trend(entries)

        assert result.months == ["2024-01", "2024-02", "2024-03"]
        assert len(result.trend) == 3
        assert result.total == Decimal("30000.0000")
        assert result.average_monthly == Decimal("10000.0000")
        assert result.peak_month == "2024-02"
        assert result.trough_month == "2024-03"

    def test_seasonality_index(self):
        entries = [
            {"month": "2024-01", "amount": "10000"},
            {"month": "2024-02", "amount": "10000"},
            {"month": "2024-03", "amount": "10000"},
        ]
        result, _ = compute_monthly_trend(entries)

        # 균등 분배 → 모든 계절성 지수 = 100
        for idx in result.seasonality_index.values():
            assert idx == Decimal("100.00")

    def test_yoy_with_prior_year(self):
        entries = [{"month": "2024-01", "amount": "12000"}]
        prior = [{"month": "2023-01", "amount": "10000"}]

        result, _ = compute_monthly_trend(entries, prior_year_entries=prior)

        assert result.trend[0].yoy_pct == Decimal("20.00")

    def test_empty_entries(self):
        result, _ = compute_monthly_trend([])
        assert result.months == []
        assert result.total == Decimal("0")
        assert len(result.warnings) > 0

    def test_high_seasonality_warning(self):
        entries = [
            {"month": "2024-01", "amount": "1000"},
            {"month": "2024-12", "amount": "50000"},
        ]
        result, _ = compute_monthly_trend(entries)

        # 큰 편차 → 계절성 경고
        assert any("SEASONALITY" in w for w in result.warnings)

    def test_aggregation_same_month(self):
        entries = [
            {"month": "2024-01", "amount": "5000"},
            {"month": "2024-01", "amount": "3000"},
        ]
        result, _ = compute_monthly_trend(entries)

        assert len(result.trend) == 1
        assert result.trend[0].amount == Decimal("8000.0000")
