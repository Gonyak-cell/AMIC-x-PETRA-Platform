"""FCF Bridge 분석 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from app.engines.fcf_engine import (
    CAPEXAnalysisResult,
    FCFBridgeResult,
    FCFPeriodData,
    compute_capex_analysis,
    compute_fcf_bridge,
)

# ── FCF Bridge ───────────────────────────────────────────


class TestComputeFCFBridge:
    def test_basic_fcf_calculation(self):
        """기본 FCF 계산: EBITDA → OCF → FCF."""
        inputs = {
            "FY2024": {
                "ebitda": "50000",
                "depreciation_amortization": "10000",
                "delta_ar": "2000",
                "delta_inventory": "1000",
                "delta_ap": "500",
                "tax_paid": "8000",
                "other_operating": "0",
                "capex": "15000",
                "other_investing": "0",
            },
        }
        result, evidence = compute_fcf_bridge(inputs)

        assert result.period_labels == ["FY2024"]
        pd = result.periods["FY2024"]

        # EBITDA
        assert pd.ebitda == Decimal("50000.0000")

        # WC Change = -AR - Inv + AP = -2000 - 1000 + 500 = -2500
        assert pd.working_capital_change == Decimal("-2500.0000")

        # OCF = EBITDA + WC - Tax + Other = 50000 - 2500 - 8000 + 0 = 39500
        assert pd.operating_cash_flow == Decimal("39500.0000")

        # FCF = OCF - CAPEX = 39500 - 15000 = 24500
        assert pd.free_cash_flow == Decimal("24500.0000")

        # CAPEX split
        assert pd.total_capex == Decimal("15000.0000")
        assert pd.maintenance_capex == Decimal("10000.0000")  # min(D&A, CAPEX)
        assert pd.growth_capex == Decimal("5000.0000")

    def test_fcf_conversion(self):
        """FCF Conversion = FCF / EBITDA."""
        inputs = {
            "FY2024": {
                "ebitda": "100000",
                "delta_ar": "0",
                "delta_inventory": "0",
                "delta_ap": "0",
                "tax_paid": "20000",
                "other_operating": "0",
                "capex": "30000",
                "other_investing": "0",
            },
        }
        result, _ = compute_fcf_bridge(inputs)
        pd = result.periods["FY2024"]

        # OCF = 100000 - 20000 = 80000; FCF = 80000 - 30000 = 50000
        assert pd.fcf_conversion == Decimal("50.00")

    def test_negative_fcf_warning(self):
        """음수 FCF → 경고 생성."""
        inputs = {
            "FY2024": {
                "ebitda": "10000",
                "delta_ar": "5000",
                "delta_inventory": "3000",
                "delta_ap": "0",
                "tax_paid": "5000",
                "other_operating": "0",
                "capex": "20000",
            },
        }
        result, _ = compute_fcf_bridge(inputs)

        assert result.periods["FY2024"].free_cash_flow < Decimal("0")
        assert any("FCF_NEGATIVE" in w for w in result.warnings)

    def test_low_conversion_warning(self):
        """낮은 FCF conversion → 경고."""
        inputs = {
            "FY2024": {
                "ebitda": "100000",
                "delta_ar": "10000",
                "delta_inventory": "10000",
                "delta_ap": "0",
                "tax_paid": "20000",
                "other_operating": "0",
                "capex": "50000",
            },
        }
        result, _ = compute_fcf_bridge(inputs)

        # OCF = 100000 - 20000 - 20000 = 60000; FCF = 60000 - 50000 = 10000
        # Conversion = 10%
        assert any("FCF_LOW_CONVERSION" in w for w in result.warnings)

    def test_multi_period(self):
        """다기간 FCF bridge."""
        inputs = {
            "FY2023": {
                "ebitda": "40000",
                "tax_paid": "6000",
                "capex": "12000",
            },
            "FY2024": {
                "ebitda": "50000",
                "tax_paid": "8000",
                "capex": "15000",
            },
        }
        result, _ = compute_fcf_bridge(inputs)

        assert result.period_labels == ["FY2023", "FY2024"]
        assert "FY2023" in result.periods
        assert "FY2024" in result.periods

    def test_bridge_items(self):
        """워터폴 차트용 bridge items 생성."""
        inputs = {
            "FY2024": {
                "ebitda": "50000",
                "tax_paid": "8000",
                "capex": "15000",
            },
        }
        result, _ = compute_fcf_bridge(inputs)

        assert len(result.bridge_items) == 7
        assert result.bridge_items[0].code == "FCF-EBITDA"
        assert result.bridge_items[0].amount == Decimal("50000.0000")
        assert result.bridge_items[-1].code == "FCF-FCF"
        assert result.bridge_items[-1].is_total is True

    def test_empty_inputs(self):
        result, _ = compute_fcf_bridge({})
        assert result.period_labels == []
        assert any("FCF_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        inputs = {
            "FY2024": {"ebitda": "50000", "tax_paid": "5000", "capex": "10000"},
        }
        _, evidence = compute_fcf_bridge(inputs)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "fcf_bridge"

    def test_negative_ebitda_warning(self):
        inputs = {
            "FY2024": {"ebitda": "-5000", "tax_paid": "0", "capex": "0"},
        }
        result, _ = compute_fcf_bridge(inputs)
        assert any("FCF_NEGATIVE_EBITDA" in w for w in result.warnings)

    def test_summary_kpis(self):
        inputs = {
            "FY2024": {"ebitda": "50000", "tax_paid": "8000", "capex": "15000"},
        }
        result, _ = compute_fcf_bridge(inputs)

        assert "latest_fcf" in result.summary_kpis
        assert "latest_ebitda" in result.summary_kpis


# ── CAPEX Analysis ───────────────────────────────────────


class TestComputeCAPEXAnalysis:
    def test_basic_capex(self):
        entries = [
            {"period": "FY2024", "capex_type": "acquisition", "amount": "15000"},
        ]
        result, evidence = compute_capex_analysis(entries)

        assert result.period_labels == ["FY2024"]
        assert result.total_capex["FY2024"] == Decimal("15000.0000")
        assert result.asset_additions["FY2024"] == Decimal("15000.0000")

    def test_maintenance_growth_split(self):
        entries = [
            {"period": "FY2024", "capex_type": "acquisition", "amount": "20000"},
        ]
        da = {"FY2024": Decimal("12000")}
        result, _ = compute_capex_analysis(entries, da_by_period=da)

        assert result.maintenance_capex["FY2024"] == Decimal("12000.0000")
        assert result.growth_capex["FY2024"] == Decimal("8000.0000")

    def test_capex_to_revenue(self):
        entries = [
            {"period": "FY2024", "capex_type": "acquisition", "amount": "10000"},
        ]
        rev = {"FY2024": Decimal("100000")}
        result, _ = compute_capex_analysis(entries, revenue_by_period=rev)

        assert result.capex_to_revenue["FY2024"] == Decimal("10.00")

    def test_capex_to_da_ratio(self):
        entries = [
            {"period": "FY2024", "capex_type": "acquisition", "amount": "18000"},
        ]
        da = {"FY2024": Decimal("12000")}
        result, _ = compute_capex_analysis(entries, da_by_period=da)

        assert result.capex_to_da["FY2024"] == Decimal("1.50")

    def test_disposal_separate(self):
        entries = [
            {"period": "FY2024", "capex_type": "acquisition", "amount": "20000"},
            {"period": "FY2024", "capex_type": "disposal", "amount": "5000"},
        ]
        result, _ = compute_capex_analysis(entries)

        assert result.asset_additions["FY2024"] == Decimal("20000.0000")
        assert result.asset_disposals["FY2024"] == Decimal("5000.0000")
        # total_capex = additions only
        assert result.total_capex["FY2024"] == Decimal("20000.0000")

    def test_empty_entries(self):
        result, _ = compute_capex_analysis([])
        assert result.period_labels == []
        assert any("CAPEX_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        entries = [
            {"period": "FY2024", "capex_type": "acquisition", "amount": "10000"},
        ]
        _, evidence = compute_capex_analysis(entries)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "capex_analysis"
