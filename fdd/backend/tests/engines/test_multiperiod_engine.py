"""다기간 재무제표 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from app.engines.multiperiod_engine import (
    DerivedMetricsRow,
    LineItemDef,
    MultiPeriodResult,
    MultiPeriodRow,
    _compute_cagr,
    _compute_yoy,
    _sort_period_labels,
    compute_derived_metrics,
    compute_multiperiod_bs,
    compute_multiperiod_fs,
    compute_multiperiod_is,
)

# ── Helpers ──────────────────────────────────────────────


def _def(
    code: str,
    name_ko: str,
    name_en: str,
    category: str,
    statement_type: str = "IS",
    order: int = 10,
    parent_code: str | None = None,
    is_subtotal: bool = False,
) -> LineItemDef:
    return LineItemDef(
        code=code,
        name_ko=name_ko,
        name_en=name_en,
        category=category,
        statement_type=statement_type,
        display_order=order,
        parent_code=parent_code,
        is_subtotal=is_subtotal,
    )


IS_DEFS = [
    _def("IS-REV", "매출액", "Revenue", "REVENUE", order=10),
    _def("IS-COGS", "매출원가", "COGS", "COGS", order=20),
    _def(
        "IS-GP",
        "매출총이익",
        "Gross Profit",
        "GROSS_PROFIT",
        order=30,
        is_subtotal=True,
    ),
    _def("IS-SGA", "판관비", "SG&A", "SGA", order=40),
]

BS_DEFS = [
    _def("BS-CASH", "현금", "Cash", "CASH", "BS", order=10),
    _def("BS-AR", "매출채권", "AR", "AR", "BS", order=20),
    _def(
        "BS-TOTAL",
        "자산총계",
        "Total Assets",
        "TOTAL",
        "BS",
        order=30,
        is_subtotal=True,
    ),
]


# ── Period Sorting ────────────────────────────────────────


class TestSortPeriodLabels:
    def test_fy_sorting(self):
        labels = ["FY2024", "FY2022", "FY2023"]
        assert _sort_period_labels(labels) == ["FY2022", "FY2023", "FY2024"]

    def test_mixed_fy_and_half(self):
        labels = ["H1 2025", "FY2024", "FY2023", "H1 2024"]
        result = _sort_period_labels(labels)
        # FY(year, 0) < H1(year, 1) — 같은 연도 내 FY가 먼저
        assert result == ["FY2023", "FY2024", "H1 2024", "H1 2025"]

    def test_quarterly_sorting(self):
        labels = ["Q3 2024", "Q1 2024", "Q4 2024", "Q2 2024"]
        result = _sort_period_labels(labels)
        assert result == ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"]

    def test_monthly_sorting(self):
        labels = ["2024-03", "2024-01", "2024-02"]
        result = _sort_period_labels(labels)
        assert result == ["2024-01", "2024-02", "2024-03"]

    def test_empty(self):
        assert _sort_period_labels([]) == []


# ── YoY Computation ───────────────────────────────────────


class TestComputeYoY:
    def test_basic_yoy(self):
        periods = {"FY2022": Decimal("100"), "FY2023": Decimal("110")}
        labels = ["FY2022", "FY2023"]
        yoy = _compute_yoy(periods, labels)
        assert "FY2023" in yoy
        assert yoy["FY2023"] == Decimal("10.00")

    def test_negative_yoy(self):
        periods = {"FY2022": Decimal("100"), "FY2023": Decimal("80")}
        yoy = _compute_yoy(periods, ["FY2022", "FY2023"])
        assert yoy["FY2023"] == Decimal("-20.00")

    def test_zero_base_skipped(self):
        periods = {"FY2022": Decimal("0"), "FY2023": Decimal("100")}
        yoy = _compute_yoy(periods, ["FY2022", "FY2023"])
        assert "FY2023" not in yoy

    def test_single_period_empty(self):
        periods = {"FY2022": Decimal("100")}
        yoy = _compute_yoy(periods, ["FY2022"])
        assert yoy == {}


# ── CAGR Computation ──────────────────────────────────────


class TestComputeCAGR:
    def test_basic_cagr(self):
        periods = {
            "FY2020": Decimal("100"),
            "FY2021": Decimal("110"),
            "FY2022": Decimal("121"),
        }
        cagr = _compute_cagr(periods, ["FY2020", "FY2021", "FY2022"])
        assert cagr is not None
        assert Decimal("9") < cagr < Decimal("11")  # ~10%

    def test_two_periods_returns_cagr(self):
        periods = {"FY2022": Decimal("100"), "FY2023": Decimal("120")}
        cagr = _compute_cagr(periods, ["FY2022", "FY2023"])
        assert cagr is not None
        assert cagr == Decimal("20.00")

    def test_single_period_returns_none(self):
        periods = {"FY2022": Decimal("100")}
        cagr = _compute_cagr(periods, ["FY2022"])
        assert cagr is None

    def test_zero_base_returns_none(self):
        periods = {"FY2022": Decimal("0"), "FY2023": Decimal("100")}
        cagr = _compute_cagr(periods, ["FY2022", "FY2023"])
        assert cagr is None

    def test_ignores_half_year_labels(self):
        periods = {
            "FY2022": Decimal("100"),
            "H1 2023": Decimal("55"),
            "FY2023": Decimal("130"),
        }
        cagr = _compute_cagr(periods, ["FY2022", "H1 2023", "FY2023"])
        assert cagr is not None
        assert cagr == Decimal("30.00")


# ── Multi-period IS ───────────────────────────────────────


class TestComputeMultiperiodIS:
    def test_single_period(self):
        amounts = {
            "FY2024": {
                "IS-REV": Decimal("-500000"),  # TB credit
                "IS-COGS": Decimal("300000"),  # TB debit
                "IS-SGA": Decimal("100000"),
            }
        }
        result, evidence = compute_multiperiod_is(amounts, IS_DEFS)

        assert result.statement_type == "IS"
        assert result.period_labels == ["FY2024"]
        assert len(result.rows) == 4  # REV, COGS, GP, SGA

        # Revenue should be sign-negated (500000)
        rev_row = next(r for r in result.rows if r.line_item_code == "IS-REV")
        assert rev_row.periods["FY2024"] == Decimal("500000.0000")

        # COGS stays positive
        cogs_row = next(r for r in result.rows if r.line_item_code == "IS-COGS")
        assert cogs_row.periods["FY2024"] == Decimal("300000.0000")

        # Evidence generated
        assert len(evidence) > 0

    def test_multi_period_with_yoy(self):
        amounts = {
            "FY2022": {"IS-REV": Decimal("-100000")},
            "FY2023": {"IS-REV": Decimal("-120000")},
        }
        result, _ = compute_multiperiod_is(amounts, IS_DEFS)

        rev_row = next(r for r in result.rows if r.line_item_code == "IS-REV")
        assert rev_row.periods["FY2022"] == Decimal("100000.0000")
        assert rev_row.periods["FY2023"] == Decimal("120000.0000")
        assert "FY2023" in rev_row.yoy_changes
        assert rev_row.yoy_changes["FY2023"] == Decimal("20.00")

    def test_empty_amounts(self):
        result, evidence = compute_multiperiod_is({}, IS_DEFS)
        assert result.period_labels == []
        assert len(result.warnings) > 0


class TestComputeMultiperiodBS:
    def test_basic_bs(self):
        amounts = {
            "FY2024": {
                "BS-CASH": Decimal("50000"),
                "BS-AR": Decimal("30000"),
            }
        }
        result, _ = compute_multiperiod_bs(amounts, BS_DEFS)
        assert result.statement_type == "BS"

        cash_row = next(r for r in result.rows if r.line_item_code == "BS-CASH")
        assert cash_row.periods["FY2024"] == Decimal("50000.0000")

        # BS should NOT negate signs
        ar_row = next(r for r in result.rows if r.line_item_code == "BS-AR")
        assert ar_row.periods["FY2024"] == Decimal("30000.0000")


# ── Derived Metrics ───────────────────────────────────────


class TestDerivedMetrics:
    def test_margins_calculated(self):
        """Revenue 100, GP 40 → Gross Margin 40%."""
        result = MultiPeriodResult(
            statement_type="IS",
            period_labels=["FY2024"],
            rows=[
                MultiPeriodRow(
                    line_item_code="IS-REV",
                    label_ko="매출액",
                    label_en="Revenue",
                    category="REVENUE",
                    display_order=10,
                    indent=0,
                    is_subtotal=False,
                    is_total=False,
                    periods={"FY2024": Decimal("100000")},
                    yoy_changes={},
                    cagr=None,
                ),
                MultiPeriodRow(
                    line_item_code="IS-GP",
                    label_ko="매출총이익",
                    label_en="Gross Profit",
                    category="GROSS_PROFIT",
                    display_order=30,
                    indent=0,
                    is_subtotal=True,
                    is_total=False,
                    periods={"FY2024": Decimal("40000")},
                    yoy_changes={},
                    cagr=None,
                ),
            ],
        )
        metrics = compute_derived_metrics(result)
        assert any(m.metric_name_en == "Gross Margin" for m in metrics)

        gm = next(m for m in metrics if m.metric_name_en == "Gross Margin")
        assert gm.periods["FY2024"] == Decimal("40.00")

    def test_no_revenue_no_metrics(self):
        result = MultiPeriodResult(
            statement_type="IS",
            period_labels=["FY2024"],
            rows=[],
        )
        assert compute_derived_metrics(result) == []
