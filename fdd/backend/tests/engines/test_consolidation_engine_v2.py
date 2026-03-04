"""연결 엔진 Phase 3 확장 단위 테스트 (IC 자동 감지, FX 변환, 엔티티 비교)."""

from decimal import Decimal

import pytest

from app.engines.consolidation_engine import (
    EntityAccountData,
    EntityPLComparison,
    FXConversionResult,
    FXRate,
    ICCandidate,
    compare_entity_pl,
    convert_fx,
    detect_ic_transactions,
)


def _acct(
    entity_id: str,
    entity_code: str,
    category: str,
    amount: str,
    account_code: str = "1000",
    account_name: str = "test",
) -> EntityAccountData:
    return EntityAccountData(
        entity_id=entity_id,
        entity_code=entity_code,
        account_code=account_code,
        account_name=account_name,
        category=category,
        amount=Decimal(amount),
    )


# ── IC 자동 감지 ─────────────────────────────────────────


class TestDetectICTransactions:
    def test_basic_ic_detection(self):
        """A의 매출 ≈ B의 매입 → IC 후보."""
        entity_accounts = {
            "E1": [
                _acct("E1", "PARENT", "REVENUE", "50000"),
                _acct("E1", "PARENT", "COGS", "30000"),
            ],
            "E2": [
                _acct("E2", "SUB", "REVENUE", "20000"),
                _acct("E2", "SUB", "COGS", "48000"),  # ≈ PARENT의 REVENUE
            ],
        }
        candidates, evidence = detect_ic_transactions(entity_accounts)

        # REVENUE(PARENT 50000) vs COGS(SUB 48000) → 4% diff → MEDIUM
        ic_revenue = [c for c in candidates if c.category == "REVENUE"]
        assert len(ic_revenue) >= 1
        assert ic_revenue[0].confidence in ("HIGH", "MEDIUM")

    def test_exact_match_high_confidence(self):
        """정확히 일치하면 HIGH confidence."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "REVENUE", "10000")],
            "E2": [_acct("E2", "B", "COGS", "10000")],
        }
        candidates, _ = detect_ic_transactions(entity_accounts)

        assert len(candidates) >= 1
        assert candidates[0].confidence == "HIGH"
        assert candidates[0].difference == Decimal("0.0000")

    def test_no_ic_when_amounts_differ(self):
        """금액 차이 > tolerance면 감지 안 됨."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "REVENUE", "10000")],
            "E2": [_acct("E2", "B", "COGS", "20000")],  # 100% 차이
        }
        candidates, _ = detect_ic_transactions(entity_accounts)

        ic_rev = [c for c in candidates if c.category == "REVENUE"]
        assert len(ic_rev) == 0

    def test_ar_ap_pair_detection(self):
        """AR ↔ AP 매칭."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "AR", "5000")],
            "E2": [_acct("E2", "B", "AP", "5000")],
        }
        candidates, _ = detect_ic_transactions(entity_accounts)

        ic_ar = [c for c in candidates if c.category == "AR"]
        assert len(ic_ar) >= 1

    def test_custom_tolerance(self):
        """커스텀 허용률."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "REVENUE", "10000")],
            "E2": [_acct("E2", "B", "COGS", "10800")],  # 8% 차이
        }
        # 기본 5% → 감지 안 됨
        cands_strict, _ = detect_ic_transactions(
            entity_accounts, tolerance_pct=Decimal("5")
        )
        ic_strict = [c for c in cands_strict if c.category == "REVENUE"]
        assert len(ic_strict) == 0

        # 10% 허용 → 감지됨
        cands_loose, _ = detect_ic_transactions(
            entity_accounts, tolerance_pct=Decimal("10")
        )
        ic_loose = [c for c in cands_loose if c.category == "REVENUE"]
        assert len(ic_loose) >= 1

    def test_evidence_generated(self):
        """Evidence 링크."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "REVENUE", "10000")],
            "E2": [_acct("E2", "B", "COGS", "10000")],
        }
        _, evidence = detect_ic_transactions(entity_accounts)
        assert len(evidence) >= 1
        assert evidence[0].source_type == "ic_detection"

    def test_single_entity_no_ic(self):
        """단일 엔티티면 IC 감지 없음."""
        entity_accounts = {
            "E1": [
                _acct("E1", "A", "REVENUE", "10000"),
                _acct("E1", "A", "COGS", "10000"),
            ],
        }
        candidates, _ = detect_ic_transactions(entity_accounts)
        assert len(candidates) == 0


# ── FX 변환 ──────────────────────────────────────────────


class TestConvertFX:
    def test_basic_conversion(self):
        """기본 환율 변환."""
        accounts = [
            _acct("E1", "SUB-USD", "REVENUE", "1000"),
            _acct("E1", "SUB-USD", "AR", "500"),
        ]
        fx = FXRate(
            source_currency="USD",
            target_currency="KRW",
            period_end_rate=Decimal("1300"),
            average_rate=Decimal("1250"),
        )
        result, evidence = convert_fx(accounts, fx)

        # REVENUE (IS) → 평균환율 1250
        rev_converted = [
            a for a in result.converted_accounts if a.category == "REVENUE"
        ]
        assert rev_converted[0].amount == Decimal("1250000.0000")

        # AR (BS) → 기말환율 1300
        ar_converted = [a for a in result.converted_accounts if a.category == "AR"]
        assert ar_converted[0].amount == Decimal("650000.0000")

    def test_all_accounts_converted(self):
        """모든 계정이 변환되었는지."""
        accounts = [
            _acct("E1", "SUB", "REVENUE", "100"),
            _acct("E1", "SUB", "COGS", "60"),
            _acct("E1", "SUB", "CASH", "200"),
        ]
        fx = FXRate(
            source_currency="USD",
            target_currency="KRW",
            period_end_rate=Decimal("1300"),
            average_rate=Decimal("1250"),
        )
        result, _ = convert_fx(accounts, fx)
        assert len(result.converted_accounts) == 3

    def test_fx_rate_divergence_warning(self):
        """환율 괴리 경고 (>10%)."""
        accounts = [_acct("E1", "SUB", "REVENUE", "100")]
        fx = FXRate(
            source_currency="USD",
            target_currency="KRW",
            period_end_rate=Decimal("1400"),  # 기말
            average_rate=Decimal("1200"),  # 평균 → 16.7% 차이
        )
        result, _ = convert_fx(accounts, fx)
        assert any("FX_RATE_DIVERGENCE" in w for w in result.warnings)

    def test_monthly_amounts_converted(self):
        """월별 금액도 변환."""
        acct = EntityAccountData(
            entity_id="E1",
            entity_code="SUB",
            account_code="1000",
            account_name="Revenue",
            category="REVENUE",
            amount=Decimal("1000"),
            monthly_amounts={"2024-01": Decimal("500"), "2024-02": Decimal("500")},
        )
        fx = FXRate(
            source_currency="USD",
            target_currency="KRW",
            period_end_rate=Decimal("1300"),
            average_rate=Decimal("1250"),
        )
        result, _ = convert_fx([acct], fx)
        converted = result.converted_accounts[0]
        assert converted.monthly_amounts["2024-01"] == Decimal("625000.0000")

    def test_evidence_generated(self):
        """Evidence 링크."""
        accounts = [_acct("E1", "SUB", "REVENUE", "100")]
        fx = FXRate(
            source_currency="EUR",
            target_currency="KRW",
            period_end_rate=Decimal("1400"),
            average_rate=Decimal("1400"),
        )
        _, evidence = convert_fx(accounts, fx)
        assert len(evidence) >= 1
        assert evidence[0].source_type == "fx_conversion"


# ── 엔티티별 P&L 비교 ───────────────────────────────────


class TestCompareEntityPL:
    def test_basic_comparison(self):
        """기본 P&L 비교."""
        entity_accounts = {
            "E1": [
                _acct("E1", "PARENT", "REVENUE", "80000"),
                _acct("E1", "PARENT", "COGS", "50000"),
            ],
            "E2": [
                _acct("E2", "SUB", "REVENUE", "20000"),
                _acct("E2", "SUB", "COGS", "15000"),
            ],
        }
        result, _ = compare_entity_pl(entity_accounts)

        assert set(result.entity_codes) == {"PARENT", "SUB"}
        assert result.total_row["REVENUE"] == Decimal("100000.0000")
        assert result.total_row["COGS"] == Decimal("65000.0000")

    def test_share_calculation(self):
        """비중 계산."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "REVENUE", "75000")],
            "E2": [_acct("E2", "B", "REVENUE", "25000")],
        }
        result, _ = compare_entity_pl(entity_accounts)

        assert result.shares["A"]["REVENUE"] == Decimal("75.00")
        assert result.shares["B"]["REVENUE"] == Decimal("25.00")

    def test_dominant_entity_warning(self):
        """지배적 엔티티 경고 (>90%)."""
        entity_accounts = {
            "E1": [_acct("E1", "MAIN", "REVENUE", "95000")],
            "E2": [_acct("E2", "SMALL", "REVENUE", "5000")],
        }
        result, _ = compare_entity_pl(entity_accounts)

        assert any("ENTITY_DOMINANT" in w for w in result.warnings)

    def test_custom_categories(self):
        """사용자 지정 카테고리."""
        entity_accounts = {
            "E1": [
                _acct("E1", "A", "REVENUE", "80000"),
                _acct("E1", "A", "COGS", "50000"),
                _acct("E1", "A", "SGA", "10000"),
            ],
            "E2": [
                _acct("E2", "B", "REVENUE", "20000"),
                _acct("E2", "B", "COGS", "15000"),
                _acct("E2", "B", "SGA", "3000"),
            ],
        }
        result, _ = compare_entity_pl(
            entity_accounts,
            categories=["REVENUE", "COGS"],
        )

        assert result.categories == ["REVENUE", "COGS"]
        assert "SGA" not in result.total_row

    def test_evidence_generated(self):
        """Evidence 링크."""
        entity_accounts = {
            "E1": [_acct("E1", "A", "REVENUE", "50000")],
            "E2": [_acct("E2", "B", "REVENUE", "50000")],
        }
        _, evidence = compare_entity_pl(entity_accounts)
        assert len(evidence) >= 1
        assert evidence[0].source_type == "entity_comparison"
