"""Consolidation Engine 테스트 — Sprint 16.

Pure function 테스트 (DB 불필요).
"""

from decimal import Decimal

from app.engines.consolidation_engine import (
    EntityAccountData,
    consolidate_entities,
)

D = Decimal


def _acct(
    entity_id: str,
    entity_code: str,
    category: str,
    amount: str,
) -> EntityAccountData:
    """Quick EntityAccountData factory."""
    return EntityAccountData(
        entity_id=entity_id,
        entity_code=entity_code,
        account_code=f"{category}-001",
        account_name=f"Test {category}",
        category=category,
        amount=D(amount),
    )


class TestConsolidateEntitiesBasic:
    """기본 연결 합산 테스트."""

    def test_two_entities_simple_aggregation(self):
        """2개 엔티티 단순 합산 (IC 없음)."""
        entity_accounts = {
            "target-id": [
                _acct("target-id", "TARGET", "REVENUE", "-100000000"),
                _acct("target-id", "TARGET", "COGS", "60000000"),
            ],
            "sub1-id": [
                _acct("sub1-id", "SUB1", "REVENUE", "-50000000"),
                _acct("sub1-id", "SUB1", "COGS", "30000000"),
            ],
        }
        ownership = {"target-id": D("100.0000"), "sub1-id": D("100.0000")}

        result, evidence = consolidate_entities(entity_accounts, ownership)

        assert result.consolidated_totals["REVENUE"] == D("-150000000")
        assert result.consolidated_totals["COGS"] == D("90000000")
        assert result.elimination_total == D("0")
        assert result.minority_interest == D("0")

    def test_multiple_categories(self):
        """BS + IS 다중 카테고리 합산."""
        entity_accounts = {
            "e1": [
                _acct("e1", "E1", "REVENUE", "-200000000"),
                _acct("e1", "E1", "COGS", "120000000"),
                _acct("e1", "E1", "CASH", "50000000"),
                _acct("e1", "E1", "AR", "30000000"),
            ],
        }
        ownership = {"e1": D("100.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership)

        assert len(result.consolidated_totals) == 4
        assert result.consolidated_totals["REVENUE"] == D("-200000000")
        assert result.consolidated_totals["CASH"] == D("50000000")
        assert result.consolidated_totals["AR"] == D("30000000")

    def test_single_entity(self):
        """단일 엔티티 — subtotals == consolidated_totals."""
        entity_accounts = {
            "only": [_acct("only", "ONLY", "REVENUE", "-10000")],
        }
        ownership = {"only": D("100.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership)

        assert result.consolidated_totals["REVENUE"] == D("-10000")
        assert result.entity_subtotals["ONLY"]["REVENUE"] == D("-10000")

    def test_empty_entity_accounts(self):
        """빈 entity_accounts → 빈 결과."""
        result, evidence = consolidate_entities({}, {})

        assert result.consolidated_totals == {}
        assert result.entity_subtotals == {}
        assert result.elimination_total == D("0")
        assert result.minority_interest == D("0")
        assert len(evidence) >= 1  # summary evidence

    def test_entity_subtotals_use_entity_code_as_key(self):
        """entity_subtotals 키는 entity_code여야 한다."""
        entity_accounts = {
            "uuid-1": [_acct("uuid-1", "TARGET", "REVENUE", "-1000")],
            "uuid-2": [_acct("uuid-2", "SUB1", "REVENUE", "-2000")],
        }
        ownership = {"uuid-1": D("100.0000"), "uuid-2": D("100.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership)

        assert "TARGET" in result.entity_subtotals
        assert "SUB1" in result.entity_subtotals
        assert "uuid-1" not in result.entity_subtotals

    def test_negative_amounts_preserved(self):
        """음수 금액 (revenue credit) 부호 보존."""
        entity_accounts = {
            "e1": [_acct("e1", "E1", "REVENUE", "-99999999.9999")],
        }
        ownership = {"e1": D("100.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership)

        assert result.consolidated_totals["REVENUE"] == D("-99999999.9999")


class TestConsolidateEntitiesICElimination:
    """IC (내부거래) 제거 테스트."""

    def test_single_ic_pair(self):
        """단일 IC pair 제거."""
        entity_accounts = {
            "e1": [_acct("e1", "TARGET", "AR", "10000000")],
            "e2": [_acct("e2", "SUB1", "AP", "10000000")],
        }
        ownership = {"e1": D("100.0000"), "e2": D("100.0000")}
        ic_pairs = [("TARGET", "SUB1", "AR", D("10000000"))]

        result, evidence = consolidate_entities(entity_accounts, ownership, ic_pairs)

        assert result.consolidated_totals["AR"] == D("0")
        assert result.elimination_total == D("10000000")
        assert len(result.eliminations) == 1
        assert result.eliminations[0].debit_entity == "TARGET"
        assert result.eliminations[0].credit_entity == "SUB1"

    def test_multiple_ic_pairs(self):
        """다중 IC pair 제거."""
        entity_accounts = {
            "e1": [
                _acct("e1", "TARGET", "AR", "20000000"),
                _acct("e1", "TARGET", "REVENUE", "-30000000"),
            ],
            "e2": [
                _acct("e2", "SUB1", "AP", "20000000"),
                _acct("e2", "SUB1", "COGS", "30000000"),
            ],
        }
        ownership = {"e1": D("100.0000"), "e2": D("100.0000")}
        ic_pairs = [
            ("TARGET", "SUB1", "AR", D("5000000")),
            ("TARGET", "SUB1", "REVENUE", D("10000000")),
        ]

        result, _ = consolidate_entities(entity_accounts, ownership, ic_pairs)

        assert result.elimination_total == D("15000000")
        assert len(result.eliminations) == 2
        assert result.consolidated_totals["AR"] == D("15000000")  # 20M - 5M IC

    def test_ic_evidence_links(self):
        """IC 제거 시 evidence link 생성."""
        entity_accounts = {
            "e1": [_acct("e1", "TARGET", "AR", "5000")],
        }
        ownership = {"e1": D("100.0000")}
        ic_pairs = [("TARGET", "SUB1", "AR", D("1000"))]

        _, evidence = consolidate_entities(entity_accounts, ownership, ic_pairs)

        ic_evidence = [e for e in evidence if e.source_type == "ic_elimination"]
        assert len(ic_evidence) == 1

    def test_no_ic_pairs(self):
        """IC pairs 없으면 elimination 없음."""
        entity_accounts = {
            "e1": [_acct("e1", "TARGET", "REVENUE", "-100")],
        }
        ownership = {"e1": D("100.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership, ic_pairs=None)

        assert result.elimination_total == D("0")
        assert len(result.eliminations) == 0


class TestConsolidateEntitiesMinorityInterest:
    """소수지분(minority interest) 테스트."""

    def test_minority_interest_80_pct(self):
        """80% 지분 → 20% 소수지분."""
        entity_accounts = {
            "sub": [_acct("sub", "SUB1", "REVENUE", "-100000")],
        }
        ownership = {"sub": D("80.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership)

        # MI = (-100000) * (100-80)/100 = -100000 * 0.20 = -20000
        assert result.minority_interest == D("-20000.0000")
        assert len(result.warnings) == 1
        assert "80.0000%" in result.warnings[0]

    def test_100_pct_no_minority_interest(self):
        """100% 지분 → 소수지분 없음."""
        entity_accounts = {
            "target": [_acct("target", "TARGET", "REVENUE", "-500000")],
        }
        ownership = {"target": D("100.0000")}

        result, _ = consolidate_entities(entity_accounts, ownership)

        assert result.minority_interest == D("0")
        assert len(result.warnings) == 0

    def test_multiple_entities_minority_aggregation(self):
        """다중 엔티티 소수지분 합산."""
        entity_accounts = {
            "target": [_acct("target", "TARGET", "REVENUE", "-1000000")],
            "sub1": [_acct("sub1", "SUB1", "REVENUE", "-200000")],
            "sub2": [_acct("sub2", "SUB2", "REVENUE", "-300000")],
        }
        ownership = {
            "target": D("100.0000"),
            "sub1": D("80.0000"),
            "sub2": D("60.0000"),
        }

        result, _ = consolidate_entities(entity_accounts, ownership)

        # sub1 MI = (-200000) * 0.20 = -40000
        # sub2 MI = (-300000) * 0.40 = -120000
        # total MI = -160000
        assert result.minority_interest == D("-160000.0000")
        assert len(result.warnings) == 2

    def test_ownership_pct_missing_defaults_to_100(self):
        """ownership_pct 누락 시 100% 기본값."""
        entity_accounts = {
            "e1": [_acct("e1", "E1", "REVENUE", "-50000")],
        }
        ownership = {}  # 비어 있음

        result, _ = consolidate_entities(entity_accounts, ownership)

        assert result.minority_interest == D("0")
        assert len(result.warnings) == 0


class TestConsolidateEntitiesEvidence:
    """Evidence link 생성 테스트."""

    def test_summary_evidence_always_present(self):
        """요약 evidence link는 항상 생성된다."""
        entity_accounts = {
            "e1": [_acct("e1", "E1", "REVENUE", "-100")],
        }
        ownership = {"e1": D("100.0000")}

        _, evidence = consolidate_entities(entity_accounts, ownership)

        summary = [e for e in evidence if e.source_type == "consolidation"]
        assert len(summary) == 1
        assert "엔티티 1개" in summary[0].detail

    def test_evidence_count_with_ic(self):
        """IC 제거 시 evidence 추가."""
        entity_accounts = {
            "e1": [_acct("e1", "TARGET", "AR", "5000")],
        }
        ownership = {"e1": D("100.0000")}
        ic_pairs = [
            ("TARGET", "SUB1", "AR", D("1000")),
            ("TARGET", "SUB1", "AP", D("2000")),
        ]

        _, evidence = consolidate_entities(entity_accounts, ownership, ic_pairs)

        # 2 IC evidence + 1 summary = 3
        assert len(evidence) == 3
