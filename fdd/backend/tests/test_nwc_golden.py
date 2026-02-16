"""NWC 골든 회귀 테스트 (30 케이스) — FDD-605.

각 시나리오는 정확한 Decimal 결과를 검증한다.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.engines.nwc_engine import (
    BSAccountData,
    NWCDefinition,
    NWCItemResult,
    calculate_nwc,
    calculate_peg,
    classify_nwc_items,
    simulate_all_pegs,
)
from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import Deal, DealDefinition, DealSnapshot, DealStatus, DealType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.seeds.standard_coa_v1 import seed_standard_line_items
from app.services.nwc.nwc_service import recalculate_peg, run_nwc_calculation
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
    monthly: dict[str, str] | None = None,
) -> BSAccountData:
    """Quick BSAccountData for NWC engine."""
    monthly_dec = {k: Decimal(v) for k, v in (monthly or {}).items()}
    return BSAccountData(
        account_code=code,
        account_name=name,
        category=category,
        amount=Decimal(amount),
        upload_file_id="upload-001",
        monthly_amounts=monthly_dec,
    )


def _item(
    code: str,
    name: str,
    category: str,
    classification: str,
    amount: str,
    is_asset: bool,
    monthly: dict[str, str] | None = None,
) -> NWCItemResult:
    """Quick NWCItemResult."""
    return NWCItemResult(
        account_code=code,
        account_name=name,
        category=category,
        classification=classification,
        amount=Decimal(amount),
        is_asset=is_asset,
        monthly_amounts=monthly or {},
    )


def _setup_deal(db: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """테스트 Deal+Def+Snapshot+UploadFile 생성.

    Returns: (deal_id, snapshot_id, upload_file_id)
    """
    deal = Deal(
        name="Golden NWC Test",
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
        file_hash="nwc_golden_hash",
        file_size_bytes=1024,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()

    defn_data = {"nwc": {"formula": "standard"}}
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
# G-NWC-01 ~ G-NWC-05: 기본 NWC 분류
# ═══════════════════════════════════════════════════════════


def test_g_nwc_01_ar_above_line():
    """G-NWC-01: AR → ABOVE_LINE, 자산 양수 그대로."""
    accounts = [_acct("1100", "매출채권", "AR", "5000000")]
    items, evidence = classify_nwc_items(accounts, NWCDefinition())
    assert len(items) == 1
    assert items[0].classification == "ABOVE_LINE"
    assert items[0].is_asset is True
    assert items[0].amount == D("5000000.0000")
    assert len(evidence) == 1


def test_g_nwc_02_multi_wc_accounts():
    """G-NWC-02: AR+Inventory+AP+Accruals 모두 ABOVE_LINE."""
    accounts = [
        _acct("1100", "매출채권", "AR", "5000000"),
        _acct("1200", "재고자산", "INVENTORY", "8000000"),
        _acct("2000", "매입채무", "AP", "-3000000"),
        _acct("2100", "미지급비용", "ACCRUALS", "-2000000"),
    ]
    items, evidence = classify_nwc_items(accounts, NWCDefinition())
    assert all(i.classification == "ABOVE_LINE" for i in items)
    assert len(evidence) == 4


def test_g_nwc_03_cash_debt_excluded():
    """G-NWC-03: Cash와 Debt는 기본 분류에서 EXCLUDED."""
    accounts = [
        _acct("1000", "현금", "CASH", "10000000"),
        _acct("2300", "단기차입금", "DEBT", "-5000000"),
    ]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert all(i.classification == "EXCLUDED" for i in items)


def test_g_nwc_04_below_line_override():
    """G-NWC-04: below_line_codes로 ABOVE → BELOW_LINE 전환."""
    defn = NWCDefinition(below_line_codes=frozenset({"1100"}))
    accounts = [_acct("1100", "매출채권", "AR", "5000000")]
    items, _ = classify_nwc_items(accounts, defn)
    assert items[0].classification == "BELOW_LINE"


def test_g_nwc_05_excluded_override():
    """G-NWC-05: excluded_codes로 ABOVE → EXCLUDED 전환."""
    defn = NWCDefinition(excluded_codes=frozenset({"1100"}))
    accounts = [_acct("1100", "매출채권", "AR", "5000000")]
    items, _ = classify_nwc_items(accounts, defn)
    assert items[0].classification == "EXCLUDED"


# ═══════════════════════════════════════════════════════════
# G-NWC-06 ~ G-NWC-10: BS 부호 규칙 및 정규화
# ═══════════════════════════════════════════════════════════


def test_g_nwc_06_asset_positive_stays():
    """G-NWC-06: 자산(양수) → 그대로 양수."""
    accounts = [_acct("1100", "매출채권", "AR", "7777777")]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].amount == D("7777777.0000")


def test_g_nwc_07_liability_negative_to_abs():
    """G-NWC-07: 부채(음수) → 절대값으로 정규화."""
    accounts = [_acct("2000", "매입채무", "AP", "-3333333")]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].amount == D("3333333.0000")
    assert items[0].is_asset is False


def test_g_nwc_08_liability_positive_stays_positive():
    """G-NWC-08: 부채가 양수면 (비정상) 그대로 양수."""
    accounts = [_acct("2000", "매입채무", "AP", "1000000")]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].amount == D("1000000.0000")


def test_g_nwc_09_other_current_assets_above_line():
    """G-NWC-09: OTHER_CURRENT_ASSETS → ABOVE_LINE."""
    accounts = [_acct("1300", "선급금", "OTHER_CURRENT_ASSETS", "2000000")]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].classification == "ABOVE_LINE"
    assert items[0].is_asset is True


def test_g_nwc_10_monthly_amounts_normalized():
    """G-NWC-10: 부채 월별 금액도 절대값으로 정규화."""
    monthly = {"2025-01": "-3000000", "2025-02": "-3500000"}
    accounts = [_acct("2000", "매입채무", "AP", "-3500000", monthly)]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].monthly_amounts["2025-01"] == "3000000.0000"
    assert items[0].monthly_amounts["2025-02"] == "3500000.0000"


# ═══════════════════════════════════════════════════════════
# G-NWC-11 ~ G-NWC-15: NWC 계산
# ═══════════════════════════════════════════════════════════


def test_g_nwc_11_simple_nwc():
    """G-NWC-11: NWC = CA - CL = 13M - 5M = 8M."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True),
        _item("1200", "재고자산", "INVENTORY", "ABOVE_LINE", "8000000", True),
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "3000000", False),
        _item("2100", "미지급비용", "ACCRUALS", "ABOVE_LINE", "2000000", False),
    ]
    result = calculate_nwc(items)
    assert result.total_current_assets == D("13000000.0000")
    assert result.total_current_liabilities == D("5000000.0000")
    assert result.net_working_capital == D("8000000.0000")


def test_g_nwc_12_assets_only():
    """G-NWC-12: 자산만 → NWC = CA."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True),
    ]
    result = calculate_nwc(items)
    assert result.total_current_assets == D("5000000.0000")
    assert result.total_current_liabilities == D("0.0000")
    assert result.net_working_capital == D("5000000.0000")


def test_g_nwc_13_liabilities_only_negative():
    """G-NWC-13: 부채만 → NWC 음수 + 경고."""
    items = [
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "10000000", False),
    ]
    result = calculate_nwc(items)
    assert result.net_working_capital == D("-10000000.0000")
    assert any("NWC_NEGATIVE" in w for w in result.warnings)


def test_g_nwc_14_empty_items():
    """G-NWC-14: 빈 항목 → NWC = 0."""
    result = calculate_nwc([])
    assert result.net_working_capital == D("0.0000")
    assert result.total_current_assets == D("0.0000")
    assert result.monthly_trend == {}


def test_g_nwc_15_below_line_excluded_from_nwc():
    """G-NWC-15: BELOW_LINE 항목은 NWC에서 제외."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True),
        _item("1300", "선급금", "OTHER_CURRENT_ASSETS", "BELOW_LINE", "3000000", True),
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "2000000", False),
    ]
    result = calculate_nwc(items)
    # CA = 5M (1300 BELOW_LINE 제외), CL = 2M
    assert result.total_current_assets == D("5000000.0000")
    assert result.net_working_capital == D("3000000.0000")


# ═══════════════════════════════════════════════════════════
# G-NWC-16 ~ G-NWC-20: 월별 트렌드
# ═══════════════════════════════════════════════════════════


def test_g_nwc_16_monthly_trend_basic():
    """G-NWC-16: 월별 CA/CL/NWC 정확도."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True,
              {"2025-01": "4500000.0000", "2025-02": "5000000.0000"}),
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "3000000", False,
              {"2025-01": "2800000.0000", "2025-02": "3000000.0000"}),
    ]
    result = calculate_nwc(items)
    assert result.monthly_trend["2025-01"]["current_assets"] == "4500000.0000"
    assert result.monthly_trend["2025-01"]["current_liabilities"] == "2800000.0000"
    assert result.monthly_trend["2025-01"]["nwc"] == "1700000.0000"
    assert result.monthly_trend["2025-02"]["nwc"] == "2000000.0000"


def test_g_nwc_17_monthly_single_month():
    """G-NWC-17: 단일 월."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True,
              {"2025-06": "5000000.0000"}),
    ]
    result = calculate_nwc(items)
    assert len(result.monthly_trend) == 1
    assert result.monthly_trend["2025-06"]["current_assets"] == "5000000.0000"
    assert result.monthly_trend["2025-06"]["current_liabilities"] == "0.0000"
    assert result.monthly_trend["2025-06"]["nwc"] == "5000000.0000"


def test_g_nwc_18_monthly_multi_account():
    """G-NWC-18: 여러 계정 월별 합산."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True,
              {"2025-01": "4000000.0000"}),
        _item("1200", "재고자산", "INVENTORY", "ABOVE_LINE", "8000000", True,
              {"2025-01": "7000000.0000"}),
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "3000000", False,
              {"2025-01": "2500000.0000"}),
    ]
    result = calculate_nwc(items)
    # CA = 4M + 7M = 11M, CL = 2.5M
    assert result.monthly_trend["2025-01"]["current_assets"] == "11000000.0000"
    assert result.monthly_trend["2025-01"]["current_liabilities"] == "2500000.0000"
    assert result.monthly_trend["2025-01"]["nwc"] == "8500000.0000"


def test_g_nwc_19_monthly_asset_only():
    """G-NWC-19: 월별 자산만 → CL = 0."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "5000000", True,
              {"2025-03": "6000000.0000"}),
    ]
    result = calculate_nwc(items)
    assert result.monthly_trend["2025-03"]["current_liabilities"] == "0.0000"


def test_g_nwc_20_monthly_liability_only():
    """G-NWC-20: 월별 부채만 → CA = 0, NWC 음수."""
    items = [
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "4000000", False,
              {"2025-03": "4000000.0000"}),
    ]
    result = calculate_nwc(items)
    assert result.monthly_trend["2025-03"]["current_assets"] == "0.0000"
    assert result.monthly_trend["2025-03"]["nwc"] == "-4000000.0000"


# ═══════════════════════════════════════════════════════════
# G-NWC-21 ~ G-NWC-25: Peg 시뮬레이션
# ═══════════════════════════════════════════════════════════


_MONTHLY_NWC = {
    "2025-01": D("7000000"),
    "2025-02": D("7500000"),
    "2025-03": D("8000000"),
    "2025-04": D("7200000"),
    "2025-05": D("8500000"),
    "2025-06": D("9000000"),
}


def test_g_nwc_21_peg_ltm_average():
    """G-NWC-21: LTM Average = (7M+7.5M+8M+7.2M+8.5M+9M)/6."""
    result = calculate_peg(_MONTHLY_NWC, "LTM_AVERAGE")
    expected = D("47200000") / D("6")
    assert result.target_nwc == expected.quantize(D("0.0001"))
    assert result.method == "LTM_AVERAGE"


def test_g_nwc_22_peg_ttm():
    """G-NWC-22: TTM = 마지막 월 (9M)."""
    result = calculate_peg(_MONTHLY_NWC, "TTM")
    assert result.target_nwc == D("9000000.0000")


def test_g_nwc_23_peg_max_min():
    """G-NWC-23: MAX=9M, MIN=7M."""
    max_r = calculate_peg(_MONTHLY_NWC, "MAX")
    min_r = calculate_peg(_MONTHLY_NWC, "MIN")
    assert max_r.target_nwc == D("9000000.0000")
    assert min_r.target_nwc == D("7000000.0000")
    # Delta: ref(9M) - max(9M)=0, ref(9M) - min(7M)=2M
    assert max_r.delta == D("0.0000")
    assert min_r.delta == D("2000000.0000")


def test_g_nwc_24_peg_custom():
    """G-NWC-24: CUSTOM value = 7777777."""
    result = calculate_peg(_MONTHLY_NWC, "CUSTOM", D("7777777"))
    assert result.target_nwc == D("7777777.0000")
    # Delta = 9M - 7777777
    assert result.delta == D("1222223.0000")


def test_g_nwc_25_simulate_all_6():
    """G-NWC-25: 6종 시나리오 전부 실행."""
    results = simulate_all_pegs(_MONTHLY_NWC, D("8000000"))
    assert len(results) == 6
    methods = {r.method for r in results}
    assert methods == {"LTM_AVERAGE", "TTM", "LAST_MONTH", "MAX", "MIN", "CUSTOM"}
    # CUSTOM target = 8M
    custom = [r for r in results if r.method == "CUSTOM"][0]
    assert custom.target_nwc == D("8000000.0000")
    assert custom.delta == D("1000000.0000")


# ═══════════════════════════════════════════════════════════
# G-NWC-26 ~ G-NWC-28: Decimal 정밀도 엣지
# ═══════════════════════════════════════════════════════════


def test_g_nwc_26_precision_four_decimals():
    """G-NWC-26: 소수점 4자리 정밀도."""
    accounts = [_acct("1100", "매출채권", "AR", "12345678.9012")]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].amount == D("12345678.9012")


def test_g_nwc_27_rounding_half_up():
    """G-NWC-27: ROUND_HALF_UP 반올림."""
    accounts = [_acct("1100", "매출채권", "AR", "12345678.90125")]
    items, _ = classify_nwc_items(accounts, NWCDefinition())
    assert items[0].amount == D("12345678.9013")


def test_g_nwc_28_large_amount():
    """G-NWC-28: 대규모 금액 정밀도."""
    items = [
        _item("1100", "매출채권", "AR", "ABOVE_LINE", "999999999999.9999", True),
        _item("2000", "매입채무", "AP", "ABOVE_LINE", "0.0001", False),
    ]
    result = calculate_nwc(items)
    assert result.net_working_capital == D("999999999999.9998")


# ═══════════════════════════════════════════════════════════
# G-NWC-29 ~ G-NWC-30: Full Pipeline E2E
# ═══════════════════════════════════════════════════════════


def test_g_nwc_29_e2e_pipeline(db: Session):
    """G-NWC-29: Full E2E — 매핑→NWC 계산 (서비스 계층)."""
    deal_id, snap_id, upload_id = _setup_deal(db)
    _insert_bs_mappings(
        db,
        deal_id,
        upload_id,
        [
            # 자산 (BS line items)
            ("1100", "매출채권", "5000000", "BS-AR-001"),
            ("1200", "재고자산", "8000000", "BS-INV-001"),
            ("1300", "선급금", "2000000", "BS-OCA-001"),
            # 부채
            ("2000", "매입채무", "-3000000", "BS-AP-001"),
            ("2100", "미지급비용", "-2000000", "BS-ACC-001"),
            # 비WC 항목 (Cash, Debt — excluded)
            ("1000", "현금", "10000000", "BS-CASH-001"),
            ("2300", "단기차입금", "-5000000", "BS-DEBT-001"),
        ],
    )

    nwc = run_nwc_calculation(db, deal_id, snap_id)
    # CA = 5M + 8M + 2M = 15M (AR + INVENTORY + OTHER_CURRENT_ASSETS)
    assert nwc.total_current_assets == D("15000000.0000")
    # CL = 3M + 2M = 5M (AP + ACCRUALS)
    assert nwc.total_current_liabilities == D("5000000.0000")
    # NWC = 15M - 5M = 10M
    assert nwc.net_working_capital == D("10000000.0000")
    assert nwc.status.value == "DRAFT"
    assert nwc.engine_version == "0.1.0"
    # 5 above-line items + 2 excluded items = 7 line items total
    assert len(nwc.line_items) == 7


def test_g_nwc_30_e2e_peg_recalculation(db: Session):
    """G-NWC-30: Full E2E + Peg 방법 변경 후 재계산.

    Note: v1 서비스는 monthly_amounts가 빈 dict이므로 monthly_trend도 비어 있고,
    calculate_peg(empty)는 target=0 을 반환한다. Peg 방법 변경 자체는 성공.
    """
    deal_id, snap_id, upload_id = _setup_deal(db)
    _insert_bs_mappings(
        db,
        deal_id,
        upload_id,
        [
            ("1100", "매출채권", "5000000", "BS-AR-001"),
            ("2000", "매입채무", "-3000000", "BS-AP-001"),
        ],
    )

    nwc = run_nwc_calculation(db, deal_id, snap_id, peg_method="LTM_AVERAGE")
    assert nwc.peg_method.value == "LTM_AVERAGE"
    # v1: monthly_trend empty → peg_target = 0
    assert nwc.monthly_trend == {}

    # Peg 방법 변경 → CUSTOM (v1에서 monthly 데이터 없으면 target=0)
    updated = recalculate_peg(db, nwc.id, "CUSTOM", D("1500000"))
    assert updated.peg_method.value == "CUSTOM"
    # monthly_nwc empty → early return, target=0 regardless of custom_value
    assert updated.peg_target == D("0.0000")
    assert updated.peg_delta == D("0.0000")
