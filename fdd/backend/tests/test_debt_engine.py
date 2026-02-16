"""Net Debt 엔진 유닛 테스트 — FDD-701/702/703/704."""

from decimal import Decimal

from app.engines.debt_engine import (
    BSAccountData,
    DebtOptions,
    calculate_net_debt,
    detect_debt_like_candidates,
)

# -- Helpers -------------------------------------------------------


def _acct(
    code: str,
    name: str,
    category: str,
    amount: str,
) -> BSAccountData:
    return BSAccountData(
        account_code=code,
        account_name=name,
        category=category,
        amount=Decimal(amount),
        upload_file_id="upload-001",
    )


# -- FDD-701: Net Debt Calculation Tests ----------------------------


class TestCalculateNetDebt:
    def _basic_accounts(self) -> list[BSAccountData]:
        return [
            # Cash
            _acct("1000", "현금및현금성자산", "CASH", "10000000"),
            _acct("1010", "단기금융상품", "CASH", "5000000"),
            # Debt (부채 음수)
            _acct("2300", "단기차입금", "DEBT", "-3000000"),
            _acct("2310", "장기차입금", "DEBT", "-7000000"),
            # Non-debt/cash items (should be ignored)
            _acct("1100", "매출채권", "AR", "8000000"),
            _acct("2000", "매입채무", "AP", "-4000000"),
        ]

    def test_basic_net_debt(self):
        result, _evidence = calculate_net_debt(self._basic_accounts(), DebtOptions())
        # Gross Debt = 3M + 7M = 10M
        assert result.gross_debt == Decimal("10000000.0000")
        # Cash = 10M + 5M = 15M
        assert result.cash_and_equivalents == Decimal("15000000.0000")
        # Net Debt = 10M - 15M = -5M
        assert result.net_debt == Decimal("-5000000.0000")
        # No debt-like/cash-like → Adjusted = Net Debt
        assert result.adjusted_net_debt == Decimal("-5000000.0000")

    def test_balance_check_zero(self):
        result, _ = calculate_net_debt(self._basic_accounts(), DebtOptions())
        assert result.balance_check_error == Decimal("0.0000")

    def test_non_debt_cash_items_excluded(self):
        result, _ = calculate_net_debt(self._basic_accounts(), DebtOptions())
        # AR, AP should not appear in items
        item_codes = {i.source_account_code for i in result.items}
        assert "1100" not in item_codes
        assert "2000" not in item_codes

    def test_evidence_links(self):
        _, evidence = calculate_net_debt(self._basic_accounts(), DebtOptions())
        # Only debt + cash items: 4 accounts
        assert len(evidence) == 4
        assert all(e.target_type == "net_debt_calculation" for e in evidence)

    def test_category_breakdown(self):
        result, _ = calculate_net_debt(self._basic_accounts(), DebtOptions())
        assert "GROSS_DEBT" in result.category_breakdown
        assert "CASH" in result.category_breakdown
        assert result.category_breakdown["GROSS_DEBT"]["count"] == 2
        assert result.category_breakdown["CASH"]["count"] == 2

    def test_negative_net_debt_warning(self):
        """현금이 차입금보다 많으면 경고."""
        result, _ = calculate_net_debt(self._basic_accounts(), DebtOptions())
        assert any("DEBT_NET_NEGATIVE" in w for w in result.warnings)

    def test_zero_amount_ignored(self):
        accounts = [_acct("2300", "단기차입금", "DEBT", "0")]
        result, _ = calculate_net_debt(accounts, DebtOptions())
        assert len(result.items) == 0

    def test_empty_accounts(self):
        result, _ = calculate_net_debt([], DebtOptions())
        assert result.gross_debt == Decimal("0.0000")
        assert result.net_debt == Decimal("0.0000")


# -- FDD-704: IFRS 16 Lease Liabilities ----------------------------


class TestLeaseOption:
    def test_lease_excluded_by_default(self):
        accounts = [
            _acct("2400", "리스부채(유동)", "LEASE_LIABILITIES", "-2000000"),
            _acct("2300", "단기차입금", "DEBT", "-5000000"),
        ]
        result, _ = calculate_net_debt(accounts, DebtOptions())
        # Lease not included
        assert result.gross_debt == Decimal("5000000.0000")
        assert result.debt_like_total == Decimal("0.0000")

    def test_lease_included_as_debt_like(self):
        accounts = [
            _acct("2400", "리스부채(유동)", "LEASE_LIABILITIES", "-2000000"),
            _acct("2300", "단기차입금", "DEBT", "-5000000"),
        ]
        opts = DebtOptions(include_lease_liabilities=True)
        result, _ = calculate_net_debt(accounts, opts)
        assert result.gross_debt == Decimal("5000000.0000")
        assert result.debt_like_total == Decimal("2000000.0000")
        assert result.adjusted_net_debt == Decimal("7000000.0000")

    def test_lease_ifrs16_warning(self):
        accounts = [_acct("2400", "리스부채", "LEASE_LIABILITIES", "-1000000")]
        opts = DebtOptions(include_lease_liabilities=True)
        result, _ = calculate_net_debt(accounts, opts)
        assert any("IFRS16" in w for w in result.warnings)


# -- FDD-703: Deferred Revenue Scenario ----------------------------


class TestDeferredRevenue:
    def test_deferred_revenue_excluded_by_default(self):
        accounts = [
            _acct("2130", "선수금", "ACCRUALS", "-3000000"),
        ]
        result, _ = calculate_net_debt(accounts, DebtOptions())
        assert result.debt_like_total == Decimal("0.0000")

    def test_deferred_revenue_included(self):
        accounts = [
            _acct("2130", "선수금", "ACCRUALS", "-3000000"),
            _acct("2300", "단기차입금", "DEBT", "-5000000"),
        ]
        opts = DebtOptions(include_deferred_revenue=True)
        result, _ = calculate_net_debt(accounts, opts)
        assert result.debt_like_total == Decimal("3000000.0000")
        # Adjusted = NetDebt + DebtLike - CashLike = 5M + 3M - 0 = 8M
        assert result.adjusted_net_debt == Decimal("8000000.0000")

    def test_deferred_revenue_english_keyword(self):
        accounts = [
            _acct("2130", "Deferred Revenue", "ACCRUALS", "-2000000"),
        ]
        opts = DebtOptions(include_deferred_revenue=True)
        result, _ = calculate_net_debt(accounts, opts)
        assert result.debt_like_total == Decimal("2000000.0000")

    def test_non_deferred_accrual_not_matched(self):
        """선수금이 아닌 미지급비용은 매칭되지 않음."""
        accounts = [
            _acct("2100", "미지급비용", "ACCRUALS", "-2000000"),
        ]
        opts = DebtOptions(include_deferred_revenue=True)
        result, _ = calculate_net_debt(accounts, opts)
        assert result.debt_like_total == Decimal("0.0000")


# -- FDD-702: Debt-like Candidate Detection -------------------------


class TestDetectDebtLikeCandidates:
    def test_lease_detected(self):
        accounts = [
            _acct("2400", "리스부채(유동)", "LEASE_LIABILITIES", "-2000000"),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 1
        assert candidates[0].detection_method == "lease_rule"
        assert candidates[0].item_type == "DEBT_LIKE"

    def test_debt_like_keyword(self):
        accounts = [
            _acct(
                "2500", "퇴직급여충당부채", "OTHER_NONCURRENT_LIABILITIES", "-5000000"
            ),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 1
        assert candidates[0].detection_method == "keyword"

    def test_deferred_revenue_detected(self):
        accounts = [
            _acct("2130", "선수금", "ACCRUALS", "-3000000"),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 1
        assert candidates[0].detection_method == "deferred_revenue_rule"

    def test_gross_debt_not_detected(self):
        """이미 DEBT 카테고리인 항목은 후보에서 제외."""
        accounts = [
            _acct("2300", "단기차입금", "DEBT", "-5000000"),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 0

    def test_cash_not_detected(self):
        accounts = [
            _acct("1000", "현금", "CASH", "10000000"),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 0

    def test_zero_amount_ignored(self):
        accounts = [
            _acct("2500", "퇴직급여충당부채", "OTHER_NONCURRENT_LIABILITIES", "0"),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 0

    def test_sorted_by_confidence_desc(self):
        accounts = [
            _acct(
                "2500", "퇴직급여충당부채", "OTHER_NONCURRENT_LIABILITIES", "-5000000"
            ),
            _acct("2400", "리스부채", "LEASE_LIABILITIES", "-2000000"),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 2
        # Lease (90) > Keyword (70)
        assert candidates[0].confidence_score > candidates[1].confidence_score

    def test_provision_keyword(self):
        accounts = [
            _acct(
                "2600",
                "Provision for Litigation",
                "OTHER_NONCURRENT_LIABILITIES",
                "-1000000",
            ),
        ]
        candidates = detect_debt_like_candidates(accounts)
        assert len(candidates) == 1
        assert "provision" in candidates[0].description.lower()
