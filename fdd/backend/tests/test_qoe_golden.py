"""QoE 골든 회귀 테스트 (30 케이스) — FDD-505.

각 시나리오는 정확한 Decimal 결과를 검증한다.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.engines.qoe_engine import (
    AdjustmentCandidateData,
    CategoryTotal,
    build_qoe_bridge,
    calculate_reported_ebitda,
    detect_adjustment_candidates,
)
from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import Deal, DealDefinition, DealSnapshot, DealStatus, DealType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.seeds.standard_coa_v1 import seed_standard_line_items
from app.services.qoe.qoe_service import run_qoe_calculation
from app.utils.hashing import hash_json

# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def seed_coa(db: Session):
    """표준 라인아이템 시드."""
    seed_standard_line_items(db)


# ── Helpers ──────────────────────────────────────────────


D = Decimal  # 축약


def _cat(cat: str, total: str, count: int = 1) -> CategoryTotal:
    """Quick CategoryTotal."""
    return CategoryTotal(
        category=cat,
        total=D(total),
        account_count=count,
        accounts=[{"code": f"{cat}-001", "name": cat, "amount": total}],
    )


def _adj(
    cat: str, amt: str, method: str = "keyword", conf: str = "70.00"
) -> AdjustmentCandidateData:
    """Quick AdjustmentCandidateData."""
    return AdjustmentCandidateData(
        category=cat,
        description=f"Test adjustment ({cat})",
        amount=D(amt),
        detection_method=method,
        confidence_score=D(conf),
    )


def _setup_deal(db: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """테스트 Deal+Def+Snapshot+UploadFile 생성.

    Returns: (deal_id, snapshot_id, upload_file_id)
    """
    deal = Deal(
        name="Golden QoE Test",
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
        file_hash="abc123",
        file_size_bytes=1024,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()

    defn_data = {"qoe": {"formula": "standard"}}
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


def _insert_tb_and_mappings(
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
# G-QOE-01 ~ G-QOE-05: 기본 EBITDA 공식 변형
# ═══════════════════════════════════════════════════════════


def test_g_qoe_01_simple_positive():
    """G-QOE-01: Simple — Rev 100M, COGS 60M, SGA 20M, D&A 5M → EBITDA 20M."""
    totals = [
        _cat("REVENUE", "-100000000"),
        _cat("COGS", "60000000"),
        _cat("SGA", "20000000"),
        _cat("DEPRECIATION_AMORTIZATION", "5000000"),
    ]
    r, _ = calculate_reported_ebitda(totals)
    assert r.reported_ebitda == D("20000000.0000")
    assert r.gross_profit == D("40000000.0000")
    assert r.operating_income == D("15000000.0000")


def test_g_qoe_02_revenue_only():
    """G-QOE-02: Revenue만 있고 비용 0 → EBITDA = Revenue."""
    r, _ = calculate_reported_ebitda([_cat("REVENUE", "-50000000")])
    assert r.reported_ebitda == D("50000000.0000")


def test_g_qoe_03_costs_only():
    """G-QOE-03: Revenue 0, COGS+SGA만 → 음수 EBITDA."""
    totals = [_cat("COGS", "30000000"), _cat("SGA", "10000000")]
    r, _ = calculate_reported_ebitda(totals)
    assert r.reported_ebitda == D("-40000000.0000")


def test_g_qoe_04_all_categories():
    """G-QOE-04: 모든 IS 카테고리 포함."""
    totals = [
        _cat("REVENUE", "-200000000"),
        _cat("COGS", "120000000"),
        _cat("SGA", "40000000"),
        _cat("DEPRECIATION_AMORTIZATION", "10000000"),
        _cat("OTHER_OPERATING_INCOME", "-5000000"),
    ]
    r, _ = calculate_reported_ebitda(totals)
    # GP = 200M - 120M = 80M
    # OI = 80M - 40M - 10M + 5M = 35M
    # EBITDA = 35M + 10M = 45M
    assert r.reported_ebitda == D("45000000.0000")


def test_g_qoe_05_zero_da():
    """G-QOE-05: D&A = 0 → EBITDA = Operating Income."""
    totals = [
        _cat("REVENUE", "-80000000"),
        _cat("COGS", "50000000"),
        _cat("SGA", "20000000"),
    ]
    r, _ = calculate_reported_ebitda(totals)
    assert r.reported_ebitda == r.operating_income


# ═══════════════════════════════════════════════════════════
# G-QOE-06 ~ G-QOE-10: 부호 규칙 엣지
# ═══════════════════════════════════════════════════════════


def test_g_qoe_06_negative_revenue_in_tb():
    """G-QOE-06: TB 매출 음수(대변) → P&L 양수."""
    r, _ = calculate_reported_ebitda([_cat("REVENUE", "-12345678")])
    assert r.revenue == D("12345678.0000")


def test_g_qoe_07_all_zeros():
    """G-QOE-07: 모든 값 0."""
    r, _ = calculate_reported_ebitda([])
    assert r.revenue == D("0.0000")
    assert r.reported_ebitda == D("0.0000")


def test_g_qoe_08_single_sga():
    """G-QOE-08: SGA만 있을 때 → 음수 EBITDA."""
    r, _ = calculate_reported_ebitda([_cat("SGA", "15000000")])
    assert r.reported_ebitda == D("-15000000.0000")


def test_g_qoe_09_other_op_debit():
    """G-QOE-09: Other Operating Expense (대변이 아닌 차변)는 음수 반전."""
    # OTHER_OPERATING_INCOME이 양수(차변)일 때 → 반전하면 음수(비용)
    totals = [
        _cat("REVENUE", "-100000000"),
        _cat("OTHER_OPERATING_INCOME", "2000000"),  # 차변=양수 → 반전→음수
    ]
    r, _ = calculate_reported_ebitda(totals)
    assert r.other_operating == D("-2000000.0000")
    assert r.reported_ebitda == D("98000000.0000")


def test_g_qoe_10_large_da_addback():
    """G-QOE-10: D&A가 매우 큰 경우 EBITDA >> Operating Income."""
    totals = [
        _cat("REVENUE", "-50000000"),
        _cat("DEPRECIATION_AMORTIZATION", "40000000"),
    ]
    r, _ = calculate_reported_ebitda(totals)
    assert r.operating_income == D("10000000.0000")
    assert r.reported_ebitda == D("50000000.0000")  # OI + D&A = 10M + 40M


# ═══════════════════════════════════════════════════════════
# G-QOE-11 ~ G-QOE-15: D&A add-back 및 Other Operating 순열
# ═══════════════════════════════════════════════════════════


def test_g_qoe_11_da_exceeds_oi():
    """G-QOE-11: Operating Income 음수이지만 D&A add-back으로 EBITDA 양수."""
    totals = [
        _cat("REVENUE", "-30000000"),
        _cat("COGS", "25000000"),
        _cat("SGA", "10000000"),
        _cat("DEPRECIATION_AMORTIZATION", "8000000"),
    ]
    r, _ = calculate_reported_ebitda(totals)
    # GP = 5M, OI = 5M - 10M - 8M = -13M, EBITDA = -13M + 8M = -5M
    assert r.operating_income == D("-13000000.0000")
    assert r.reported_ebitda == D("-5000000.0000")


def test_g_qoe_12_other_op_positive_and_negative():
    """G-QOE-12: Other Operating이 순수익일 때."""
    totals = [
        _cat("REVENUE", "-100000000"),
        _cat("COGS", "60000000"),
        _cat("SGA", "25000000"),
        _cat("DEPRECIATION_AMORTIZATION", "5000000"),
        _cat("OTHER_OPERATING_INCOME", "-8000000"),  # 8M 수익
    ]
    r, _ = calculate_reported_ebitda(totals)
    # GP=40M, OI=40M-25M-5M+8M=18M, EBITDA=18M+5M=23M
    assert r.reported_ebitda == D("23000000.0000")


def test_g_qoe_13_multiple_revenue_accounts():
    """G-QOE-13: 여러 매출 계정 합산."""
    totals = [
        CategoryTotal(
            "REVENUE",
            D("-70000000"),
            3,
            [
                {"code": "4100", "name": "제품매출", "amount": "-40000000"},
                {"code": "4200", "name": "용역매출", "amount": "-20000000"},
                {"code": "4300", "name": "기타매출", "amount": "-10000000"},
            ],
        ),
        _cat("COGS", "35000000"),
    ]
    r, evidence = calculate_reported_ebitda(totals)
    assert r.revenue == D("70000000.0000")
    assert len(evidence) == 4  # 3 revenue + 1 COGS


def test_g_qoe_14_da_only():
    """G-QOE-14: D&A만 있을 때 → EBITDA = 0 (D&A - D&A = 0)."""
    r, _ = calculate_reported_ebitda([_cat("DEPRECIATION_AMORTIZATION", "5000000")])
    # OI = -5M, EBITDA = -5M + 5M = 0
    assert r.reported_ebitda == D("0.0000")


def test_g_qoe_15_mixed_positive_negative_other_op():
    """G-QOE-15: Other Operating에 수익+비용 혼합 합계."""
    totals = [
        _cat("REVENUE", "-100000000"),
        CategoryTotal(
            "OTHER_OPERATING_INCOME",
            D("3000000"),
            2,
            [
                {"code": "7100", "name": "기타영업수익", "amount": "-5000000"},
                {"code": "7200", "name": "기타영업비용", "amount": "8000000"},
            ],
        ),
    ]
    r, _ = calculate_reported_ebitda(totals)
    # net other_op = -(3000000) = -3M
    assert r.other_operating == D("-3000000.0000")
    assert r.reported_ebitda == D("97000000.0000")


# ═══════════════════════════════════════════════════════════
# G-QOE-16 ~ G-QOE-20: Bridge 밸런스 검증
# ═══════════════════════════════════════════════════════════


def test_g_qoe_16_bridge_no_adjustments():
    """G-QOE-16: 조정 0건 → Adjusted = Reported."""
    bridge = build_qoe_bridge(D("20000000.0000"), [])
    assert bridge.adjusted_ebitda == D("20000000.0000")
    assert bridge.balance_check_error == D("0.0000")


def test_g_qoe_17_bridge_single_positive():
    """G-QOE-17: 단일 양수 조정."""
    bridge = build_qoe_bridge(
        D("20000000.0000"), [_adj("NON_RECURRING", "5000000.0000")]
    )
    assert bridge.adjusted_ebitda == D("25000000.0000")
    assert bridge.balance_check_error == D("0.0000")


def test_g_qoe_18_bridge_single_negative():
    """G-QOE-18: 단일 음수 조정."""
    bridge = build_qoe_bridge(
        D("20000000.0000"), [_adj("NORMALIZATION", "-3000000.0000")]
    )
    assert bridge.adjusted_ebitda == D("17000000.0000")
    assert bridge.balance_check_error == D("0.0000")


def test_g_qoe_19_bridge_mixed_adjustments():
    """G-QOE-19: 양수+음수 혼합 조정."""
    adjs = [
        _adj("NON_RECURRING", "5000000.0000"),
        _adj("NON_OPERATING", "-2000000.0000"),
        _adj("NORMALIZATION", "1000000.0000"),
    ]
    bridge = build_qoe_bridge(D("20000000.0000"), adjs)
    assert bridge.total_adjustments == D("4000000.0000")
    assert bridge.adjusted_ebitda == D("24000000.0000")
    assert bridge.balance_check_error == D("0.0000")


def test_g_qoe_20_bridge_large_negative_result():
    """G-QOE-20: 조정으로 Adjusted EBITDA 음수."""
    adjs = [_adj("NON_RECURRING", "-30000000.0000")]
    bridge = build_qoe_bridge(D("20000000.0000"), adjs)
    assert bridge.adjusted_ebitda == D("-10000000.0000")
    assert bridge.balance_check_error == D("0.0000")


# ═══════════════════════════════════════════════════════════
# G-QOE-21 ~ G-QOE-25: 조정 탐지 (keyword, non_operating, year_end)
# ═══════════════════════════════════════════════════════════


def test_g_qoe_21_detect_litigation():
    """G-QOE-21: 소송 키워드 감지."""
    gl = [
        {
            "entry_id": "G21",
            "account_code": "9100",
            "account_name": "소송비용",
            "amount": "50000000",
            "description": "소송 합의금",
            "entry_date": "2025-06-15",
        }
    ]
    cands = detect_adjustment_candidates(gl, set(), D("1000000000"))
    assert len(cands) == 1
    assert cands[0].category == "NON_RECURRING"


def test_g_qoe_22_detect_restructuring():
    """G-QOE-22: 구조조정 키워드."""
    gl = [
        {
            "entry_id": "G22",
            "account_code": "9200",
            "account_name": "비용",
            "amount": "30000000",
            "description": "구조조정비",
            "entry_date": "2025-03-01",
        }
    ]
    cands = detect_adjustment_candidates(gl, set(), D("1000000000"))
    assert len(cands) == 1
    assert "구조조정" in cands[0].description


def test_g_qoe_23_detect_non_operating():
    """G-QOE-23: 비영업 계정 감지."""
    gl = [
        {
            "entry_id": "G23",
            "account_code": "NON-1",
            "account_name": "외환차손",
            "amount": "15000000",
            "description": "외환차손",
            "entry_date": "2025-05-01",
        }
    ]
    cands = detect_adjustment_candidates(gl, {"NON-1"}, D("1000000000"))
    assert len(cands) == 1
    assert cands[0].category == "NON_OPERATING"


def test_g_qoe_24_detect_year_end():
    """G-QOE-24: 연말 대규모 전표."""
    gl = [
        {
            "entry_id": "G24",
            "account_code": "5100",
            "account_name": "잡비",
            "amount": "80000000",
            "description": "기말 대체 분개",
            "entry_date": "2025-12-31",
        }
    ]
    # Materiality = max(100M * 1%, 1M) = 1M. 5x = 5M. 80M >= 5M → match
    cands = detect_adjustment_candidates(gl, set(), D("100000000"))
    assert len(cands) == 1
    assert cands[0].detection_method == "year_end"


def test_g_qoe_25_detect_owner_related():
    """G-QOE-25: 오너/관계사 키워드 → NORMALIZATION."""
    gl = [
        {
            "entry_id": "G25",
            "account_code": "8100",
            "account_name": "급여",
            "amount": "20000000",
            "description": "대표이사 급여",
            "entry_date": "2025-07-01",
        }
    ]
    cands = detect_adjustment_candidates(gl, set(), D("1000000000"))
    assert len(cands) == 1
    assert cands[0].category == "NORMALIZATION"


# ═══════════════════════════════════════════════════════════
# G-QOE-26 ~ G-QOE-28: Decimal 정밀도 엣지
# ═══════════════════════════════════════════════════════════


def test_g_qoe_26_precision_four_decimals():
    """G-QOE-26: 소수점 4자리 정밀도."""
    r, _ = calculate_reported_ebitda([_cat("REVENUE", "-12345678.9012")])
    assert r.revenue == D("12345678.9012")


def test_g_qoe_27_rounding():
    """G-QOE-27: 반올림 (ROUND_HALF_UP)."""
    # -12345678.90125 → 반전 → 12345678.90125 → quantize(0.0001) = 12345678.9013
    r, _ = calculate_reported_ebitda([_cat("REVENUE", "-12345678.90125")])
    assert r.revenue == D("12345678.9013")


def test_g_qoe_28_bridge_precision():
    """G-QOE-28: Bridge 대규모 금액 정밀도."""
    adjs = [
        _adj("NON_RECURRING", "0.0001"),
        _adj("NON_OPERATING", "-0.0001"),
    ]
    bridge = build_qoe_bridge(D("999999999999.9999"), adjs)
    assert bridge.total_adjustments == D("0.0000")
    assert bridge.adjusted_ebitda == D("999999999999.9999")
    assert bridge.balance_check_error == D("0.0000")


# ═══════════════════════════════════════════════════════════
# G-QOE-29 ~ G-QOE-30: Full Pipeline E2E
# ═══════════════════════════════════════════════════════════


def test_g_qoe_29_e2e_pipeline(db: Session):
    """G-QOE-29: Full E2E — 매핑→QoE→Bridge (서비스 계층)."""
    deal_id, snap_id, upload_id = _setup_deal(db)
    _insert_tb_and_mappings(
        db,
        deal_id,
        upload_id,
        [
            ("4100", "매출액", "-100000000", "IS-REV-001"),
            ("5100", "매출원가", "60000000", "IS-COGS-001"),
            ("6100", "판관비", "20000000", "IS-SGA-001"),
            ("6200", "감가상각비", "5000000", "IS-DA-001"),
        ],
    )

    qoe = run_qoe_calculation(db, deal_id, snap_id)
    assert qoe.reported_ebitda == D("20000000.0000")
    assert qoe.adjusted_ebitda == D("20000000.0000")  # No approved adjs yet
    assert qoe.balance_check_error == D("0.0000")
    assert qoe.status.value == "DRAFT"


def test_g_qoe_30_e2e_with_gl_detection(db: Session):
    """G-QOE-30: Full E2E + GL 조정 후보 탐지."""
    deal_id, snap_id, upload_id = _setup_deal(db)
    _insert_tb_and_mappings(
        db,
        deal_id,
        upload_id,
        [
            ("4100", "매출액", "-100000000", "IS-REV-001"),
            ("5100", "매출원가", "60000000", "IS-COGS-001"),
            ("6100", "판관비", "20000000", "IS-SGA-001"),
        ],
    )

    # GL with keyword entries
    for entry_data in [
        (
            "GL-001",
            "2025-06-15",
            "9100",
            "소송비용",
            Decimal("50000000"),
            "소송 합의금",
        ),
        ("GL-002", "2025-12-31", "9200", "기타비용", Decimal("80000000"), "연말 대체"),
    ]:
        db.add(
            JournalEntry(
                deal_id=deal_id,
                upload_file_id=upload_id,
                source_type="GL",
                entry_id=entry_data[0],
                entry_date=date.fromisoformat(entry_data[1]),
                account_code=entry_data[2],
                account_name=entry_data[3],
                debit=entry_data[4],
                amount=entry_data[4],
                description=entry_data[5],
                row_number=1,
            )
        )
    db.commit()

    qoe = run_qoe_calculation(db, deal_id, snap_id)
    assert qoe.reported_ebitda == D("20000000.0000")

    # Should have detected candidates
    candidates = [a for a in qoe.adjustments if a.status.value == "CANDIDATE"]
    assert len(candidates) >= 1  # At least litigation keyword match
