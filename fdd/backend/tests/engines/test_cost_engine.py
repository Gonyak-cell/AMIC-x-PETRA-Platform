"""비용 구조 분석 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from app.engines.cost_engine import (
    ManufacturingCostResult,
    PersonnelCostResult,
    SGABreakdownResult,
    compute_manufacturing_cost,
    compute_personnel_cost,
    compute_sga_breakdown,
)

# ── Helpers ──────────────────────────────────────────────


def _cost_entry(
    period: str = "FY2024",
    category: str = "direct_material",
    amount: str = "0",
) -> dict:
    return {"period": period, "cost_category": category, "amount": amount}


def _sga_entry(
    period: str = "FY2024",
    account_name: str = "",
    amount: str = "0",
) -> dict:
    return {"period": period, "account_name": account_name, "amount": amount}


def _personnel_entry(
    period: str = "FY2024",
    department: str = "전체",
    amount: str = "0",
) -> dict:
    return {"period": period, "department": department, "amount": amount}


# ── Manufacturing Cost ───────────────────────────────────


class TestComputeManufacturingCost:
    def test_basic_three_elements(self):
        """3요소 기본 집계."""
        entries = [
            _cost_entry(category="direct_material", amount="50000"),
            _cost_entry(category="direct_labor", amount="30000"),
            _cost_entry(category="manufacturing_overhead", amount="20000"),
        ]
        result, evidence = compute_manufacturing_cost(entries)

        assert result.period_labels == ["FY2024"]
        assert result.direct_materials["FY2024"] == Decimal("50000.0000")
        assert result.direct_labor["FY2024"] == Decimal("30000.0000")
        assert result.manufacturing_overhead["FY2024"] == Decimal("20000.0000")
        assert result.total_cogs["FY2024"] == Decimal("100000.0000")

    def test_ratios(self):
        """비율 계산: 재료비 50%, 인건비 30%, 경비 20%."""
        entries = [
            _cost_entry(category="direct_material", amount="50000"),
            _cost_entry(category="direct_labor", amount="30000"),
            _cost_entry(category="manufacturing_overhead", amount="20000"),
        ]
        result, _ = compute_manufacturing_cost(entries)

        assert result.material_ratio["FY2024"] == Decimal("50.00")
        assert result.labor_ratio["FY2024"] == Decimal("30.00")
        assert result.overhead_ratio["FY2024"] == Decimal("20.00")

    def test_korean_category_names(self):
        """한글 카테고리명 지원."""
        entries = [
            _cost_entry(category="직접재료비", amount="40000"),
            _cost_entry(category="노무비", amount="35000"),
            _cost_entry(category="제조경비", amount="25000"),
        ]
        result, _ = compute_manufacturing_cost(entries)

        assert result.direct_materials["FY2024"] == Decimal("40000.0000")
        assert result.direct_labor["FY2024"] == Decimal("35000.0000")
        assert result.manufacturing_overhead["FY2024"] == Decimal("25000.0000")

    def test_multi_period(self):
        """다기간 집계."""
        entries = [
            _cost_entry(period="FY2023", category="direct_material", amount="40000"),
            _cost_entry(period="FY2024", category="direct_material", amount="50000"),
        ]
        result, _ = compute_manufacturing_cost(entries)

        assert result.period_labels == ["FY2023", "FY2024"]
        assert result.direct_materials["FY2023"] == Decimal("40000.0000")
        assert result.direct_materials["FY2024"] == Decimal("50000.0000")

    def test_empty_entries(self):
        result, _ = compute_manufacturing_cost([])
        assert result.period_labels == []
        assert any("COST_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        entries = [
            _cost_entry(category="direct_material", amount="50000"),
        ]
        _, evidence = compute_manufacturing_cost(entries)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "manufacturing_cost"


# ── SGA Breakdown ────────────────────────────────────────


class TestComputeSGABreakdown:
    def test_basic_breakdown(self):
        entries = [
            _sga_entry(account_name="급여", amount="20000"),
            _sga_entry(account_name="임차료", amount="10000"),
            _sga_entry(account_name="광고선전비", amount="5000"),
        ]
        result, _ = compute_sga_breakdown(entries)

        assert result.period_labels == ["FY2024"]
        assert len(result.items) == 3
        assert result.items[0].name_ko == "급여"  # 최대 금액이 1위
        assert result.total_sga["FY2024"] == Decimal("35000.0000")

    def test_top_n_with_others(self):
        entries = [
            _sga_entry(account_name="급여", amount="20000"),
            _sga_entry(account_name="임차료", amount="10000"),
            _sga_entry(account_name="광고비", amount="5000"),
            _sga_entry(account_name="접대비", amount="3000"),
            _sga_entry(account_name="통신비", amount="2000"),
        ]
        result, _ = compute_sga_breakdown(entries, top_n=3)

        assert len(result.items) == 4  # Top 3 + 기타
        assert result.items[3].name_ko == "기타"

    def test_sga_to_revenue_ratio(self):
        entries = [
            _sga_entry(account_name="급여", amount="20000"),
        ]
        rev = {"FY2024": Decimal("100000")}
        result, _ = compute_sga_breakdown(entries, revenue_by_period=rev)

        assert result.sga_to_revenue_ratio["FY2024"] == Decimal("20.00")

    def test_share_pct(self):
        entries = [
            _sga_entry(account_name="A", amount="60000"),
            _sga_entry(account_name="B", amount="40000"),
        ]
        result, _ = compute_sga_breakdown(entries)

        assert result.items[0].share_pct == Decimal("60.00")
        assert result.items[1].share_pct == Decimal("40.00")

    def test_yoy_calculation(self):
        entries = [
            _sga_entry(period="FY2023", account_name="급여", amount="10000"),
            _sga_entry(period="FY2024", account_name="급여", amount="12000"),
        ]
        result, _ = compute_sga_breakdown(entries)

        assert result.items[0].yoy_pct == Decimal("20.00")

    def test_empty_entries(self):
        result, _ = compute_sga_breakdown([])
        assert result.period_labels == []
        assert any("SGA_EMPTY" in w for w in result.warnings)


# ── Personnel Cost ───────────────────────────────────────


class TestComputePersonnelCost:
    def test_basic_personnel(self):
        entries = [
            _personnel_entry(amount="50000"),
        ]
        result, _ = compute_personnel_cost(entries)

        assert result.period_labels == ["FY2024"]
        assert result.total_personnel["FY2024"] == Decimal("50000.0000")

    def test_cost_per_head(self):
        entries = [
            _personnel_entry(amount="60000"),
        ]
        headcount = {"FY2024": 100}
        result, _ = compute_personnel_cost(entries, headcount_by_period=headcount)

        assert result.cost_per_head["FY2024"] == Decimal("600.0000")

    def test_personnel_to_revenue(self):
        entries = [
            _personnel_entry(amount="30000"),
        ]
        rev = {"FY2024": Decimal("100000")}
        result, _ = compute_personnel_cost(entries, revenue_by_period=rev)

        assert result.personnel_to_revenue["FY2024"] == Decimal("30.00")

    def test_department_breakdown(self):
        entries = [
            _personnel_entry(department="영업부", amount="20000"),
            _personnel_entry(department="개발부", amount="30000"),
        ]
        result, _ = compute_personnel_cost(entries)

        assert len(result.department_breakdown) == 2
        assert result.department_breakdown[0].name_ko == "개발부"  # 금액 큰 순

    def test_empty_entries(self):
        result, _ = compute_personnel_cost([])
        assert result.period_labels == []
        assert any("PERSONNEL_EMPTY" in w for w in result.warnings)

    def test_no_headcount_no_per_head(self):
        entries = [
            _personnel_entry(amount="50000"),
        ]
        result, _ = compute_personnel_cost(entries)
        assert result.cost_per_head == {}  # headcount 없으면 계산 불가
