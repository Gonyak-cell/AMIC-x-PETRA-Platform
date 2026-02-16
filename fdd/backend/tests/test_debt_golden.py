"""Net Debt 골든 회귀 테스트 (30 케이스) — FDD-705.

각 시나리오는 정확한 Decimal 결과를 검증한다.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.engines.debt_engine import (
    BSAccountData,
    DebtOptions,
    calculate_net_debt,
    detect_debt_like_candidates,
)
from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import Deal, DealDefinition, DealSnapshot, DealStatus, DealType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.seeds.standard_coa_v1 import seed_standard_line_items
from app.services.debt.debt_service import run_net_debt_calculation
from app.utils.hashing import hash_json

# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def seed_coa(db: Session):
    """표준 라인아이템 시드."""
    seed_standard_line_items(db)


# ── Helpers ──────────────────────────────────────────────

D = Decimal  # 축약


def _acct(
    code: str,
    name: str,
    category: str,
    amount: str,
) -> BSAccountData:
    """Quick BSAccountData for Debt engine."""
    return BSAccountData(
        account_code=code,
        account_name=name,
        category=category,
        amount=Decimal(amount),
        upload_file_id="upload-001",
    )


def _setup_deal(db: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """테스트 Deal+Def+Snapshot+UploadFile 생성.

    Returns: (deal_id, snapshot_id, upload_file_id)
    """
    deal = Deal(
        name="Golden Debt Test",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        status=DealStatus.ACTIVE,
    )
    db.add(deal)
    db.flush()

    upload = UploadFile(
        deal_id=deal.id,
        original_filename="test_tb.xlsx",
        stored_path="/tmp/test_tb.xlsx",
        file_hash="debt_golden_hash",
        file_size_bytes=1024,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()

    defn_data = {"debt": {"formula": "standard"}}
    defn = DealDefinition(
        deal_id=deal.id,
        version=1,
        definition_data=defn_data,
        hash=hash_json(defn_data),
    )
    db.add(defn)
    db.flush()

    snap = DealSnapshot(
        deal_id=deal.id,
        definition_version_id=defn.id,
        engine_version="0.1.0",
        input_hash=hash_json({"def": defn.hash}),
        status="RUNNING",
    )
    db.add(snap)
    db.flush()
    db.commit()
    return deal.id, snap.id, upload.id


def _insert_bs_mappings(
    db: Session,
    deal_id: uuid.UUID,
    upload_file_id: uuid.UUID,
    accounts: list[tuple[str, str, str, str]],
) -> None:
    """TB + APPROVED 매핑. accounts: [(code, name, balance, target_code)]."""
    for code, name, balance, target in accounts:
        db.add(
            JournalEntry(
                deal_id=deal_id,
                upload_file_id=upload_file_id,
                source_type="TB",
                account_code=code,
                account_name=name,
                balance=D(balance),
                row_number=1,
            )
        )
        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code=code,
                source_account_name=name,
                target_line_item_code=target,
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.APPROVED,
                match_score=D("100.00"),
                algorithm="exact",
                affected_amount=D(balance),
                approved_by="test",
            )
        )
    db.commit()


# ═══════════════════════════════════════════════════════════
# G-DEBT-01 ~ G-DEBT-05: 기본 Net Debt 계산
# ═══════════════════════════════════════════════════════════


def test_g_debt_01_simple_net_debt():
    """G-DEBT-01: Net Debt = Gross Debt(10M) - Cash(15M) = -5M."""
    accounts = [
        _acct("1000", "현금", "CASH", "10000000"),
        _acct("1010", "단기금융상품", "CASH", "5000000"),
        _acct("2300", "단기차입금", "DEBT", "-3000000"),
        _acct("2310", "장기차입금", "DEBT", "-7000000"),
    ]
    result, evidence = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("10000000.0000")
    assert result.cash_and_equivalents == D("15000000.0000")
    assert result.net_debt == D("-5000000.0000")
    assert result.adjusted_net_debt == D("-5000000.0000")
    assert len(evidence) == 4


def test_g_debt_02_debt_only():
    """G-DEBT-02: Debt만 → 양수 Net Debt."""
    accounts = [
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
        _acct("2310", "장기차입금", "DEBT", "-10000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("15000000.0000")
    assert result.cash_and_equivalents == D("0.0000")
    assert result.net_debt == D("15000000.0000")


def test_g_debt_03_cash_only():
    """G-DEBT-03: Cash만 → 음수 Net Debt + 경고."""
    accounts = [
        _acct("1000", "현금", "CASH", "20000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("0.0000")
    assert result.net_debt == D("-20000000.0000")
    assert any("DEBT_NET_NEGATIVE" in w for w in result.warnings)


def test_g_debt_04_both_zero():
    """G-DEBT-04: 모두 0 → Net Debt = 0."""
    result, _ = calculate_net_debt([], DebtOptions())
    assert result.gross_debt == D("0.0000")
    assert result.net_debt == D("0.0000")
    assert result.adjusted_net_debt == D("0.0000")


def test_g_debt_05_multiple_accounts():
    """G-DEBT-05: 다수 계정 합산 검증."""
    accounts = [
        _acct("1000", "현금", "CASH", "10000000"),
        _acct("1010", "단기금융", "CASH", "5000000"),
        _acct("1020", "제한예금", "CASH", "3000000"),
        _acct("2300", "단기차입금", "DEBT", "-8000000"),
        _acct("2310", "장기차입금", "DEBT", "-12000000"),
        _acct("2320", "사채", "DEBT", "-5000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("25000000.0000")  # 8+12+5=25
    assert result.cash_and_equivalents == D("18000000.0000")  # 10+5+3=18
    assert result.net_debt == D("7000000.0000")  # 25-18=7


# ═══════════════════════════════════════════════════════════
# G-DEBT-06 ~ G-DEBT-10: BS 부호 규칙 및 필터링
# ═══════════════════════════════════════════════════════════


def test_g_debt_06_debt_abs_value():
    """G-DEBT-06: 부채 음수 → 절대값으로 변환."""
    accounts = [_acct("2300", "단기차입금", "DEBT", "-7777777")]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("7777777.0000")
    assert result.items[0].amount == D("7777777.0000")


def test_g_debt_07_cash_positive():
    """G-DEBT-07: Cash 양수 → 그대로."""
    accounts = [_acct("1000", "현금", "CASH", "3333333")]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.cash_and_equivalents == D("3333333.0000")


def test_g_debt_08_zero_amount_ignored():
    """G-DEBT-08: 잔액 0인 항목 무시."""
    accounts = [
        _acct("2300", "단기차입금", "DEBT", "0"),
        _acct("1000", "현금", "CASH", "0"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert len(result.items) == 0
    assert result.net_debt == D("0.0000")


def test_g_debt_09_non_debt_cash_excluded():
    """G-DEBT-09: AR/AP/Inventory 등 비 Debt/Cash 항목은 제외."""
    accounts = [
        _acct("1100", "매출채권", "AR", "8000000"),
        _acct("2000", "매입채무", "AP", "-4000000"),
        _acct("1200", "재고자산", "INVENTORY", "6000000"),
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    # Only debt item
    assert result.gross_debt == D("5000000.0000")
    assert result.cash_and_equivalents == D("0.0000")
    item_codes = {i.source_account_code for i in result.items}
    assert "1100" not in item_codes
    assert "2000" not in item_codes


def test_g_debt_10_balance_check_always_zero():
    """G-DEBT-10: Balance check error는 항상 0."""
    accounts = [
        _acct("1000", "현금", "CASH", "10000000"),
        _acct("2300", "차입금", "DEBT", "-5000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.balance_check_error == D("0.0000")


# ═══════════════════════════════════════════════════════════
# G-DEBT-11 ~ G-DEBT-15: IFRS 16 리스 & 이연수익
# ═══════════════════════════════════════════════════════════


def test_g_debt_11_lease_excluded_by_default():
    """G-DEBT-11: 리스부채 기본 제외."""
    accounts = [
        _acct("2400", "리스부채(유동)", "LEASE_LIABILITIES", "-2000000"),
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("5000000.0000")
    assert result.debt_like_total == D("0.0000")


def test_g_debt_12_lease_included():
    """G-DEBT-12: include_lease_liabilities=True → DEBT_LIKE로 포함."""
    accounts = [
        _acct("2400", "리스부채(유동)", "LEASE_LIABILITIES", "-2000000"),
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
    ]
    opts = DebtOptions(include_lease_liabilities=True)
    result, _ = calculate_net_debt(accounts, opts)
    assert result.gross_debt == D("5000000.0000")
    assert result.debt_like_total == D("2000000.0000")
    # Adjusted = 5M - 0(cash) + 2M(debt-like) - 0(cash-like) = 7M
    assert result.adjusted_net_debt == D("7000000.0000")
    assert any("IFRS16" in w for w in result.warnings)


def test_g_debt_13_deferred_revenue_excluded():
    """G-DEBT-13: 선수금 기본 제외."""
    accounts = [
        _acct("2130", "선수금", "ACCRUALS", "-3000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.debt_like_total == D("0.0000")
    assert len(result.items) == 0


def test_g_debt_14_deferred_revenue_included():
    """G-DEBT-14: include_deferred_revenue=True → 선수금 DEBT_LIKE."""
    accounts = [
        _acct("2130", "선수금", "ACCRUALS", "-3000000"),
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
    ]
    opts = DebtOptions(include_deferred_revenue=True)
    result, _ = calculate_net_debt(accounts, opts)
    assert result.debt_like_total == D("3000000.0000")
    assert result.adjusted_net_debt == D("8000000.0000")


def test_g_debt_15_lease_and_deferred_together():
    """G-DEBT-15: 리스 + 이연수익 모두 포함."""
    accounts = [
        _acct("1000", "현금", "CASH", "10000000"),
        _acct("2300", "단기차입금", "DEBT", "-20000000"),
        _acct("2400", "리스부채", "LEASE_LIABILITIES", "-3000000"),
        _acct("2130", "선수금", "ACCRUALS", "-2000000"),
    ]
    opts = DebtOptions(include_lease_liabilities=True, include_deferred_revenue=True)
    result, _ = calculate_net_debt(accounts, opts)
    assert result.gross_debt == D("20000000.0000")
    assert result.cash_and_equivalents == D("10000000.0000")
    assert result.net_debt == D("10000000.0000")
    assert result.debt_like_total == D("5000000.0000")  # 3M + 2M
    assert result.adjusted_net_debt == D("15000000.0000")  # 10M + 5M
    assert result.balance_check_error == D("0.0000")


# ═══════════════════════════════════════════════════════════
# G-DEBT-16 ~ G-DEBT-20: Debt-like 후보 탐지
# ═══════════════════════════════════════════════════════════


def test_g_debt_16_lease_candidate():
    """G-DEBT-16: LEASE_LIABILITIES → lease_rule 후보."""
    accounts = [
        _acct("2400", "리스부채(유동)", "LEASE_LIABILITIES", "-2000000"),
    ]
    candidates = detect_debt_like_candidates(accounts)
    assert len(candidates) == 1
    assert candidates[0].detection_method == "lease_rule"
    assert candidates[0].confidence_score == D("90.00")


def test_g_debt_17_keyword_retirement():
    """G-DEBT-17: 퇴직급여 키워드 → keyword 후보."""
    accounts = [
        _acct("2500", "퇴직급여충당부채", "OTHER_NONCURRENT_LIABILITIES", "-5000000"),
    ]
    candidates = detect_debt_like_candidates(accounts)
    assert len(candidates) == 1
    assert candidates[0].detection_method == "keyword"
    assert candidates[0].confidence_score == D("70.00")


def test_g_debt_18_deferred_revenue_candidate():
    """G-DEBT-18: 선수금 → deferred_revenue_rule 후보."""
    accounts = [
        _acct("2130", "선수금", "ACCRUALS", "-3000000"),
    ]
    candidates = detect_debt_like_candidates(accounts)
    assert len(candidates) == 1
    assert candidates[0].detection_method == "deferred_revenue_rule"
    assert candidates[0].confidence_score == D("75.00")


def test_g_debt_19_debt_cash_excluded_from_candidates():
    """G-DEBT-19: DEBT/CASH 카테고리 항목은 후보에서 제외."""
    accounts = [
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
        _acct("1000", "현금", "CASH", "10000000"),
    ]
    candidates = detect_debt_like_candidates(accounts)
    assert len(candidates) == 0


def test_g_debt_20_candidates_sorted_by_confidence():
    """G-DEBT-20: 후보 목록은 confidence DESC 정렬."""
    accounts = [
        _acct("2500", "퇴직급여충당부채", "OTHER_NONCURRENT_LIABILITIES", "-5000000"),
        _acct("2400", "리스부채", "LEASE_LIABILITIES", "-2000000"),
        _acct("2130", "선수금", "ACCRUALS", "-3000000"),
    ]
    candidates = detect_debt_like_candidates(accounts)
    assert len(candidates) == 3
    # lease(90) > deferred(75) > keyword(70)
    assert candidates[0].confidence_score == D("90.00")
    assert candidates[1].confidence_score == D("75.00")
    assert candidates[2].confidence_score == D("70.00")


# ═══════════════════════════════════════════════════════════
# G-DEBT-21 ~ G-DEBT-25: Adjusted Net Debt & 검증
# ═══════════════════════════════════════════════════════════


def test_g_debt_21_adjusted_formula():
    """G-DEBT-21: Adjusted = Net Debt + Debt-like - Cash-like."""
    accounts = [
        _acct("1000", "현금", "CASH", "5000000"),
        _acct("2300", "단기차입금", "DEBT", "-10000000"),
        _acct("2400", "리스부채", "LEASE_LIABILITIES", "-3000000"),
    ]
    opts = DebtOptions(include_lease_liabilities=True)
    result, _ = calculate_net_debt(accounts, opts)
    # Net Debt = 10M - 5M = 5M
    # Adjusted = 5M + 3M = 8M
    assert result.net_debt == D("5000000.0000")
    assert result.debt_like_total == D("3000000.0000")
    assert result.adjusted_net_debt == D("8000000.0000")


def test_g_debt_22_deferred_english_keyword():
    """G-DEBT-22: 영문 'Deferred Revenue' 키워드 매칭."""
    accounts = [
        _acct("2130", "Deferred Revenue", "ACCRUALS", "-2000000"),
    ]
    opts = DebtOptions(include_deferred_revenue=True)
    result, _ = calculate_net_debt(accounts, opts)
    assert result.debt_like_total == D("2000000.0000")


def test_g_debt_23_non_deferred_accrual_not_matched():
    """G-DEBT-23: 이연수익 아닌 미지급비용은 매칭 안 됨."""
    accounts = [
        _acct("2100", "미지급비용", "ACCRUALS", "-2000000"),
    ]
    opts = DebtOptions(include_deferred_revenue=True)
    result, _ = calculate_net_debt(accounts, opts)
    assert result.debt_like_total == D("0.0000")


def test_g_debt_24_category_breakdown():
    """G-DEBT-24: Category breakdown 검증."""
    accounts = [
        _acct("1000", "현금", "CASH", "10000000"),
        _acct("1010", "단기금융", "CASH", "5000000"),
        _acct("2300", "단기차입금", "DEBT", "-3000000"),
        _acct("2310", "장기차입금", "DEBT", "-7000000"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert "GROSS_DEBT" in result.category_breakdown
    assert "CASH" in result.category_breakdown
    assert result.category_breakdown["GROSS_DEBT"]["count"] == 2
    assert result.category_breakdown["CASH"]["count"] == 2
    assert result.category_breakdown["GROSS_DEBT"]["total"] == "10000000.0000"
    assert result.category_breakdown["CASH"]["total"] == "15000000.0000"


def test_g_debt_25_warnings():
    """G-DEBT-25: 경고 메시지 검증."""
    accounts = [_acct("1000", "현금", "CASH", "20000000")]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert any("DEBT_NET_NEGATIVE" in w for w in result.warnings)

    # IFRS 16 warning
    accounts2 = [_acct("2400", "리스부채", "LEASE_LIABILITIES", "-1000000")]
    opts = DebtOptions(include_lease_liabilities=True)
    result2, _ = calculate_net_debt(accounts2, opts)
    assert any("IFRS16" in w for w in result2.warnings)


# ═══════════════════════════════════════════════════════════
# G-DEBT-26 ~ G-DEBT-28: Decimal 정밀도 엣지
# ═══════════════════════════════════════════════════════════


def test_g_debt_26_precision_four_decimals():
    """G-DEBT-26: 소수점 4자리 정밀도."""
    accounts = [_acct("2300", "단기차입금", "DEBT", "-12345678.9012")]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("12345678.9012")


def test_g_debt_27_rounding_half_up():
    """G-DEBT-27: ROUND_HALF_UP 반올림."""
    accounts = [_acct("2300", "단기차입금", "DEBT", "-12345678.90125")]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("12345678.9013")


def test_g_debt_28_large_amount():
    """G-DEBT-28: 대규모 금액 정밀도."""
    accounts = [
        _acct("2300", "차입금", "DEBT", "-999999999999.9999"),
        _acct("1000", "현금", "CASH", "0.0001"),
    ]
    result, _ = calculate_net_debt(accounts, DebtOptions())
    assert result.gross_debt == D("999999999999.9999")
    assert result.cash_and_equivalents == D("0.0001")
    assert result.net_debt == D("999999999999.9998")
    assert result.balance_check_error == D("0.0000")


# ═══════════════════════════════════════════════════════════
# G-DEBT-29 ~ G-DEBT-30: Full Pipeline E2E
# ═══════════════════════════════════════════════════════════


def test_g_debt_29_e2e_pipeline(db: Session):
    """G-DEBT-29: Full E2E — 매핑→Net Debt 계산 (서비스 계층)."""
    deal_id, snap_id, upload_id = _setup_deal(db)
    _insert_bs_mappings(
        db,
        deal_id,
        upload_id,
        [
            # Cash
            ("1000", "현금및현금성자산", "10000000", "BS-CASH-001"),
            ("1010", "단기금융상품", "5000000", "BS-CASH-002"),
            # Debt
            ("2300", "단기차입금", "-3000000", "BS-DEBT-001"),
            ("2310", "장기차입금", "-7000000", "BS-DEBT-002"),
            # Non-debt (AR, AP — should be ignored)
            ("1100", "매출채권", "8000000", "BS-AR-001"),
            ("2000", "매입채무", "-4000000", "BS-AP-001"),
        ],
    )

    calc = run_net_debt_calculation(db, deal_id, snap_id)
    assert calc.gross_debt == D("10000000.0000")
    assert calc.cash_and_equivalents == D("15000000.0000")
    assert calc.net_debt == D("-5000000.0000")
    assert calc.adjusted_net_debt == D("-5000000.0000")
    assert calc.balance_check_error == D("0.0000")
    assert calc.status.value == "DRAFT"
    assert calc.engine_version == "0.1.0"
    # 4 items (2 cash + 2 debt), AR/AP excluded
    classified_codes = {i.source_account_code for i in calc.items}
    assert "1100" not in classified_codes
    assert "2000" not in classified_codes


def test_g_debt_30_e2e_with_lease_option(db: Session):
    """G-DEBT-30: Full E2E + IFRS 16 리스부채 옵션."""
    deal_id, snap_id, upload_id = _setup_deal(db)
    _insert_bs_mappings(
        db,
        deal_id,
        upload_id,
        [
            ("1000", "현금및현금성자산", "10000000", "BS-CASH-001"),
            ("2300", "단기차입금", "-5000000", "BS-DEBT-001"),
            ("2400", "리스부채(유동)", "-2000000", "BS-LEASE-001"),
            ("2500", "퇴직급여충당부채", "-3000000", "BS-ONCL-001"),
        ],
    )

    calc = run_net_debt_calculation(
        db, deal_id, snap_id, include_lease_liabilities=True
    )
    assert calc.gross_debt == D("5000000.0000")
    assert calc.cash_and_equivalents == D("10000000.0000")
    assert calc.net_debt == D("-5000000.0000")
    # Lease included as debt-like
    assert calc.debt_like_total == D("2000000.0000")
    assert calc.adjusted_net_debt == D("-3000000.0000")  # -5M + 2M = -3M
    assert calc.include_lease_liabilities is True
    # 퇴직급여 is detected as candidate
    candidate_items = [
        i for i in calc.items if i.detection_method == "keyword"
    ]
    assert len(candidate_items) >= 1
