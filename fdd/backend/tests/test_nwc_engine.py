"""NWC 엔진 유닛 테스트 — FDD-601/602/603."""

from decimal import Decimal

from app.engines.nwc_engine import (
    BSAccountData,
    NWCDefinition,
    NWCItemResult,
    calculate_nwc,
    calculate_peg,
    classify_nwc_items,
    simulate_all_pegs,
)

# -- Helpers -------------------------------------------------------


def _acct(
    code: str,
    name: str,
    category: str,
    amount: str,
    monthly: dict[str, str] | None = None,
) -> BSAccountData:
    monthly_dec = {k: Decimal(v) for k, v in (monthly or {}).items()}
    return BSAccountData(
        account_code=code,
        account_name=name,
        category=category,
        amount=Decimal(amount),
        upload_file_id="upload-001",
        monthly_amounts=monthly_dec,
    )


def _default_definition() -> NWCDefinition:
    return NWCDefinition()


# -- FDD-601: Classification Tests ---------------------------------


class TestClassifyNWCItems:
    def test_ar_classified_above_line(self):
        accounts = [_acct("1100", "매출채권", "AR", "5000000")]
        items, _evidence = classify_nwc_items(accounts, _default_definition())
        assert len(items) == 1
        assert items[0].classification == "ABOVE_LINE"
        assert items[0].is_asset is True
        assert items[0].amount == Decimal("5000000.0000")

    def test_ap_classified_above_line(self):
        """부채는 TB에서 음수 → 절대값으로 정규화."""
        accounts = [_acct("2000", "매입채무", "AP", "-3000000")]
        items, _ = classify_nwc_items(accounts, _default_definition())
        assert items[0].classification == "ABOVE_LINE"
        assert items[0].is_asset is False
        assert items[0].amount == Decimal("3000000.0000")

    def test_cash_excluded_by_default(self):
        accounts = [_acct("1000", "현금", "CASH", "10000000")]
        items, _ = classify_nwc_items(accounts, _default_definition())
        assert items[0].classification == "EXCLUDED"

    def test_debt_excluded_by_default(self):
        accounts = [_acct("2300", "단기차입금", "DEBT", "-5000000")]
        items, _ = classify_nwc_items(accounts, _default_definition())
        assert items[0].classification == "EXCLUDED"

    def test_below_line_override(self):
        defn = NWCDefinition(below_line_codes=frozenset({"1100"}))
        accounts = [_acct("1100", "매출채권", "AR", "5000000")]
        items, _ = classify_nwc_items(accounts, defn)
        assert items[0].classification == "BELOW_LINE"

    def test_excluded_override(self):
        defn = NWCDefinition(excluded_codes=frozenset({"1100"}))
        accounts = [_acct("1100", "매출채권", "AR", "5000000")]
        items, _ = classify_nwc_items(accounts, defn)
        assert items[0].classification == "EXCLUDED"

    def test_inventory_above_line(self):
        accounts = [_acct("1200", "재고자산", "INVENTORY", "8000000")]
        items, _ = classify_nwc_items(accounts, _default_definition())
        assert items[0].classification == "ABOVE_LINE"
        assert items[0].category == "INVENTORY"

    def test_accruals_above_line(self):
        accounts = [_acct("2100", "미지급비용", "ACCRUALS", "-2000000")]
        items, _ = classify_nwc_items(accounts, _default_definition())
        assert items[0].classification == "ABOVE_LINE"
        assert items[0].amount == Decimal("2000000.0000")

    def test_evidence_links_generated(self):
        accounts = [
            _acct("1100", "매출채권", "AR", "5000000"),
            _acct("2000", "매입채무", "AP", "-3000000"),
        ]
        _, evidence = classify_nwc_items(accounts, _default_definition())
        assert len(evidence) == 2
        assert evidence[0].target_type == "nwc_calculation"
        assert evidence[0].source_type == "TB"

    def test_monthly_amounts_normalized(self):
        """부채 월별 금액도 절대값으로 정규화."""
        monthly = {"2025-01": "-3000000", "2025-02": "-3500000"}
        accounts = [_acct("2000", "매입채무", "AP", "-3500000", monthly)]
        items, _ = classify_nwc_items(accounts, _default_definition())
        assert items[0].monthly_amounts["2025-01"] == "3000000.0000"
        assert items[0].monthly_amounts["2025-02"] == "3500000.0000"


# -- FDD-602: NWC Calculation Tests --------------------------------


class TestCalculateNWC:
    def _make_items(self) -> list[NWCItemResult]:
        return [
            NWCItemResult(
                account_code="1100",
                account_name="매출채권",
                category="AR",
                classification="ABOVE_LINE",
                amount=Decimal("5000000"),
                is_asset=True,
                monthly_amounts={"2025-01": "4500000.0000", "2025-02": "5000000.0000"},
            ),
            NWCItemResult(
                account_code="1200",
                account_name="재고자산",
                category="INVENTORY",
                classification="ABOVE_LINE",
                amount=Decimal("8000000"),
                is_asset=True,
                monthly_amounts={"2025-01": "7500000.0000", "2025-02": "8000000.0000"},
            ),
            NWCItemResult(
                account_code="2000",
                account_name="매입채무",
                category="AP",
                classification="ABOVE_LINE",
                amount=Decimal("3000000"),
                is_asset=False,
                monthly_amounts={"2025-01": "2800000.0000", "2025-02": "3000000.0000"},
            ),
            NWCItemResult(
                account_code="2100",
                account_name="미지급비용",
                category="ACCRUALS",
                classification="ABOVE_LINE",
                amount=Decimal("2000000"),
                is_asset=False,
                monthly_amounts={"2025-01": "1800000.0000", "2025-02": "2000000.0000"},
            ),
            # Below-the-line item (should be excluded from NWC)
            NWCItemResult(
                account_code="1300",
                account_name="선급금",
                category="OTHER_CURRENT_ASSETS",
                classification="BELOW_LINE",
                amount=Decimal("1000000"),
                is_asset=True,
                monthly_amounts={"2025-01": "1000000.0000", "2025-02": "1000000.0000"},
            ),
        ]

    def test_nwc_calculation(self):
        result = calculate_nwc(self._make_items())
        # CA = 5M + 8M = 13M, CL = 3M + 2M = 5M
        assert result.total_current_assets == Decimal("13000000.0000")
        assert result.total_current_liabilities == Decimal("5000000.0000")
        assert result.net_working_capital == Decimal("8000000.0000")

    def test_below_line_excluded_from_nwc(self):
        result = calculate_nwc(self._make_items())
        # 선급금(BELOW_LINE)은 NWC에 포함되지 않음
        assert result.total_current_assets == Decimal("13000000.0000")

    def test_monthly_trend(self):
        result = calculate_nwc(self._make_items())
        assert "2025-01" in result.monthly_trend
        jan = result.monthly_trend["2025-01"]
        # CA = 4.5M + 7.5M = 12M, CL = 2.8M + 1.8M = 4.6M
        assert jan["current_assets"] == "12000000.0000"
        assert jan["current_liabilities"] == "4600000.0000"
        assert jan["nwc"] == "7400000.0000"

    def test_category_breakdown(self):
        result = calculate_nwc(self._make_items())
        assert "AR" in result.category_breakdown
        assert "INVENTORY" in result.category_breakdown
        assert "AP" in result.category_breakdown
        assert result.category_breakdown["AR"]["total"] == "5000000.0000"

    def test_empty_items(self):
        result = calculate_nwc([])
        assert result.net_working_capital == Decimal("0.0000")
        assert result.monthly_trend == {}

    def test_negative_nwc_warning(self):
        items = [
            NWCItemResult(
                account_code="2000",
                account_name="매입채무",
                category="AP",
                classification="ABOVE_LINE",
                amount=Decimal("10000000"),
                is_asset=False,
                monthly_amounts={},
            ),
        ]
        result = calculate_nwc(items)
        assert result.net_working_capital < Decimal("0")
        assert any("NWC_NEGATIVE" in w for w in result.warnings)


# -- FDD-603: Peg Simulation Tests ---------------------------------


class TestPegCalculation:
    def _monthly_nwc(self) -> dict[str, Decimal]:
        return {
            "2025-01": Decimal("7000000"),
            "2025-02": Decimal("7500000"),
            "2025-03": Decimal("8000000"),
            "2025-04": Decimal("7200000"),
            "2025-05": Decimal("8500000"),
            "2025-06": Decimal("9000000"),
        }

    def test_ltm_average(self):
        result = calculate_peg(self._monthly_nwc(), "LTM_AVERAGE")
        # Average of 6 values
        expected = (
            Decimal("7000000")
            + Decimal("7500000")
            + Decimal("8000000")
            + Decimal("7200000")
            + Decimal("8500000")
            + Decimal("9000000")
        ) / Decimal("6")
        assert result.target_nwc == expected.quantize(Decimal("0.0001"))
        assert result.method == "LTM_AVERAGE"

    def test_last_month(self):
        result = calculate_peg(self._monthly_nwc(), "LAST_MONTH")
        assert result.target_nwc == Decimal("9000000.0000")

    def test_ttm(self):
        result = calculate_peg(self._monthly_nwc(), "TTM")
        assert result.target_nwc == Decimal("9000000.0000")

    def test_max(self):
        result = calculate_peg(self._monthly_nwc(), "MAX")
        assert result.target_nwc == Decimal("9000000.0000")

    def test_min(self):
        result = calculate_peg(self._monthly_nwc(), "MIN")
        assert result.target_nwc == Decimal("7000000.0000")

    def test_custom(self):
        result = calculate_peg(self._monthly_nwc(), "CUSTOM", Decimal("7777777"))
        assert result.target_nwc == Decimal("7777777.0000")

    def test_delta_calculation(self):
        result = calculate_peg(self._monthly_nwc(), "LTM_AVERAGE")
        # delta = reference NWC (last = 9M) - target
        expected_delta = Decimal("9000000") - result.target_nwc
        assert result.delta == expected_delta.quantize(Decimal("0.0001"))

    def test_empty_monthly(self):
        result = calculate_peg({}, "LTM_AVERAGE")
        assert result.target_nwc == Decimal("0")

    def test_simulate_all_6_scenarios(self):
        results = simulate_all_pegs(self._monthly_nwc(), Decimal("8000000"))
        assert len(results) == 6
        methods = {r.method for r in results}
        assert methods == {"LTM_AVERAGE", "TTM", "LAST_MONTH", "MAX", "MIN", "CUSTOM"}
