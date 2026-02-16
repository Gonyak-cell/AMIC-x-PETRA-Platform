"""골든 회귀 테스트 — 20개 시나리오.

CoA 매핑 → Tie-out → Evidence 전체 파이프라인을 E2E로 검증.
각 시나리오는 TB 계정 목록 + 예상 매핑 결과 + 예상 tie-out 상태를 포함한다.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.account_mapping import MappingConfidence
from app.models.deal import (
    Deal,
    DealDefinition,
    DealSnapshot,
    DealType,
    DefinitionStatus,
    SnapshotStatus,
)
from app.models.evidence import SourceType
from app.models.journal_entry import JournalEntry
from app.models.standard_line_item import (
    FinancialStatement,
    StandardLineItem,
)
from app.models.tie_out import TieOutStatus
from app.models.upload import IngestionStatus, UploadFile
from app.schemas.evidence import EvidenceLinkCreate
from app.schemas.mapping import AccountMappingCreate
from app.services.evidence.detector import detect_missing_evidence
from app.services.evidence.ledger_service import create_evidence_link
from app.services.mapping.coa_mapper import save_mappings, suggest_mappings
from app.services.mapping.tie_out import validate_tie_out
from app.utils.hashing import hash_json

# ── Fixture: 80개 표준 라인아이템 시드 ─────────────────────


@pytest.fixture(autouse=True)
def seed_coa(db: Session):
    """모든 골든 테스트에 표준 라인아이템을 시드."""
    from app.seeds.standard_coa_v1 import seed_standard_line_items

    seed_standard_line_items(db)


def _setup_deal(db: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Deal + Definition + Snapshot + UploadFile 생성.

    Returns: (deal_id, snapshot_id, upload_file_id)
    """
    deal = Deal(
        name="Golden Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.flush()

    defn = DealDefinition(
        deal_id=deal.id,
        version=1,
        definition_data={"golden": True},
        status=DefinitionStatus.APPROVED,
        hash=hash_json({"golden": True}),
    )
    db.add(defn)
    db.flush()

    snap = DealSnapshot(
        deal_id=deal.id,
        definition_version_id=defn.id,
        engine_version="0.1.0",
        input_hash="golden",
        status=SnapshotStatus.RUNNING,
    )
    db.add(snap)
    db.flush()

    uf = UploadFile(
        deal_id=deal.id,
        original_filename="golden_tb.xlsx",
        stored_path="/tmp/golden.xlsx",
        file_hash="goldenhash",
        file_size_bytes=2048,
        status=IngestionStatus.COMPLETED,
    )
    db.add(uf)
    db.flush()

    return deal.id, snap.id, uf.id


def _insert_tb(
    db: Session,
    deal_id: uuid.UUID,
    upload_id: uuid.UUID,
    accounts: list[tuple[str, str, Decimal]],
) -> None:
    for i, (code, name, balance) in enumerate(accounts, 1):
        db.add(
            JournalEntry(
                upload_file_id=upload_id,
                deal_id=deal_id,
                source_type="TB",
                row_number=i,
                account_code=code,
                account_name=name,
                balance=balance,
            )
        )
    db.commit()


def _get_line_items(db: Session) -> list[StandardLineItem]:
    from sqlalchemy import select

    return list(db.scalars(select(StandardLineItem)).all())


# ── Golden Regression Scenarios ───────────────────────────
# 각 시나리오: (TB 데이터, 예상 매칭 코드, 예상 알고리즘)

GOLDEN_SCENARIOS = [
    # 1. 매출액 정확 매칭
    {
        "id": "G01",
        "tb": [("1001", "매출액", Decimal("10000000"))],
        "expected": [("IS-REV-001", "exact")],
    },
    # 2. 매출원가 정확 매칭
    {
        "id": "G02",
        "tb": [("2001", "매출원가", Decimal("7000000"))],
        "expected": [("IS-COGS-001", "exact")],
    },
    # 3. 판매비와관리비 정확 매칭
    {
        "id": "G03",
        "tb": [("3001", "판매비와관리비", Decimal("2000000"))],
        "expected": [("IS-SGA-001", "exact")],
    },
    # 4. 급여 정확 매칭
    {
        "id": "G04",
        "tb": [("3010", "급여", Decimal("1200000"))],
        "expected": [("IS-SGA-002", "exact")],
    },
    # 5. 현금및현금성자산 정확 매칭
    {
        "id": "G05",
        "tb": [("4001", "현금및현금성자산", Decimal("5000000"))],
        "expected": [("BS-CASH-001", "exact")],
    },
    # 6. 매출채권 정확 매칭
    {
        "id": "G06",
        "tb": [("4100", "매출채권", Decimal("3000000"))],
        "expected": [("BS-AR-001", "exact")],
    },
    # 7. 재고자산 정확 매칭
    {
        "id": "G07",
        "tb": [("4200", "재고자산", Decimal("2500000"))],
        "expected": [("BS-INV-001", "exact")],
    },
    # 8. 매입채무 정확 매칭
    {
        "id": "G08",
        "tb": [("5001", "매입채무", Decimal("-1500000"))],
        "expected": [("BS-AP-001", "exact")],
    },
    # 9. 키워드 매칭 — "급여비용" → 급여(IS-SGA-002)
    {
        "id": "G09",
        "tb": [("3011", "급여비용", Decimal("800000"))],
        "expected": [("IS-SGA-002", "keyword")],
    },
    # 10. 키워드 매칭 — "제품매출" → IS-REV-002
    {
        "id": "G10",
        "tb": [("1002", "제품매출계정", Decimal("4000000"))],
        "expected": [("IS-REV-002", "keyword")],
    },
    # 11. 키워드 매칭 — "단기차입금대출" → BS-DEBT-001
    {
        "id": "G11",
        "tb": [("6001", "단기차입금대출", Decimal("-2000000"))],
        "expected": [("BS-DEBT-001", "keyword")],
    },
    # 12. 키워드 매칭 — "임차료비용" → IS-SGA-003
    {
        "id": "G12",
        "tb": [("3020", "임차료비용", Decimal("600000"))],
        "expected": [("IS-SGA-003", "keyword")],
    },
    # 13. 영문 정확 매칭 — "Revenue"
    {
        "id": "G13",
        "tb": [("E001", "Revenue", Decimal("15000000"))],
        "expected": [("IS-REV-001", "exact")],
    },
    # 14. 영문 키워드 매칭 — "Total Sales Amount"
    {
        "id": "G14",
        "tb": [("E002", "Total Sales Amount", Decimal("12000000"))],
        "expected": [("IS-REV-001", "keyword")],
    },
    # 15. 미매핑 — 알 수 없는 계정
    {
        "id": "G15",
        "tb": [("9999", "XYZABC특수계정", Decimal("100"))],
        "expected": [("", "none")],
    },
    # 16. 혼합 — exact + keyword + unmapped
    {
        "id": "G16",
        "tb": [
            ("1001", "매출액", Decimal("10000000")),
            ("3011", "급여비용", Decimal("800000")),
            ("9999", "XYZABC", Decimal("50")),
        ],
        "expected": [
            ("IS-REV-001", "exact"),
            ("IS-SGA-002", "keyword"),
            ("", "none"),
        ],
    },
    # 17. 자본금 정확 매칭
    {
        "id": "G17",
        "tb": [("7001", "자본금", Decimal("100000000"))],
        "expected": [("BS-EQ-001", "exact")],
    },
    # 18. 이익잉여금 정확 매칭
    {
        "id": "G18",
        "tb": [("7003", "이익잉여금", Decimal("50000000"))],
        "expected": [("BS-EQ-003", "exact")],
    },
    # 19. 감가상각비 키워드 매칭
    {
        "id": "G19",
        "tb": [("3050", "감가상각비계정", Decimal("400000"))],
        "expected": [("IS-DA-001", "keyword")],
    },
    # 20. 대규모 혼합 — IS/BS 전부
    {
        "id": "G20",
        "tb": [
            ("1001", "매출액", Decimal("100000000")),
            ("2001", "매출원가", Decimal("60000000")),
            ("3001", "판매비와관리비", Decimal("20000000")),
            ("4001", "현금및현금성자산", Decimal("30000000")),
            ("5001", "매입채무", Decimal("-10000000")),
            ("7001", "자본금", Decimal("50000000")),
        ],
        "expected": [
            ("IS-REV-001", "exact"),
            ("IS-COGS-001", "exact"),
            ("IS-SGA-001", "exact"),
            ("BS-CASH-001", "exact"),
            ("BS-AP-001", "exact"),
            ("BS-EQ-001", "exact"),
        ],
    },
]


# ── Parametrized Golden Tests ─────────────────────────────


@pytest.mark.parametrize(
    "scenario",
    GOLDEN_SCENARIOS,
    ids=[s["id"] for s in GOLDEN_SCENARIOS],
)
def test_golden_mapping(scenario: dict, db: Session):
    """골든 데이터로 매핑 엔진 결과를 회귀 검증한다."""
    line_items = _get_line_items(db)

    tb_accounts = [(code, name, balance) for code, name, balance in scenario["tb"]]

    suggestions = suggest_mappings(line_items, tb_accounts)
    assert len(suggestions) == len(scenario["expected"])

    for suggestion, (expected_code, expected_algo) in zip(
        suggestions, scenario["expected"], strict=True
    ):
        assert suggestion.suggested_target_code == expected_code, (
            f"[{scenario['id']}] {suggestion.source_account_name}: "
            f"expected {expected_code}, got {suggestion.suggested_target_code}"
        )
        assert suggestion.algorithm == expected_algo, (
            f"[{scenario['id']}] {suggestion.source_account_name}: "
            f"expected algo={expected_algo}, got {suggestion.algorithm}"
        )


# ── E2E Pipeline Tests ────────────────────────────────────


class TestGoldenE2EPipeline:
    """매핑 → 저장 → 승인 → Tie-out → Evidence 전체 파이프라인."""

    def test_full_pipeline_pass(self, db: Session):
        """모든 IS 계정 매핑 + 승인 → Tie-out PASS."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        line_items = _get_line_items(db)

        # TB 데이터 삽입
        _insert_tb(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출액", Decimal("10000000")),
                ("2001", "매출원가", Decimal("6000000")),
            ],
        )

        # 매핑 제안
        tb_accounts = [
            ("1001", "매출액", Decimal("10000000")),
            ("2001", "매출원가", Decimal("6000000")),
        ]
        suggestions = suggest_mappings(line_items, tb_accounts)
        assert len(suggestions) == 2

        # 매핑 저장
        create_data = [
            AccountMappingCreate(
                source_account_code=s.source_account_code,
                source_account_name=s.source_account_name,
                target_line_item_code=s.suggested_target_code,
                confidence=s.confidence,
                match_score=s.match_score,
                algorithm=s.algorithm,
                affected_amount=s.affected_amount,
            )
            for s in suggestions
            if s.suggested_target_code
        ]
        saved = save_mappings(db, deal_id, create_data)
        assert len(saved) == 2

        # 전체 승인
        from app.services.mapping.coa_mapper import approve_mapping as approve_fn

        for m in saved:
            approve_fn(db, m, "golden_tester")

        # Tie-out 검증
        is_result, _bs_result = validate_tie_out(db, deal_id, snapshot_id)
        assert is_result.status == TieOutStatus.PASS
        assert is_result.variance == Decimal("0")

    def test_full_pipeline_with_evidence(self, db: Session):
        """매핑 + Evidence 연결 → 누락 탐지 coverage 100%."""
        deal_id, _snapshot_id, upload_id = _setup_deal(db)
        _get_line_items(db)

        _insert_tb(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출액", Decimal("5000000")),
            ],
        )

        # 매핑
        create_data = [
            AccountMappingCreate(
                source_account_code="1001",
                source_account_name="매출액",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                match_score=Decimal("100.00"),
                algorithm="exact",
                affected_amount=Decimal("5000000"),
            ),
        ]
        saved = save_mappings(db, deal_id, create_data)
        from app.services.mapping.coa_mapper import approve_mapping as approve_fn

        approve_fn(db, saved[0], "golden_tester")

        # Evidence 연결
        create_evidence_link(
            db,
            deal_id,
            EvidenceLinkCreate(
                target_type="account_mapping",
                target_id=saved[0].id,
                source_type=SourceType.TB,
                source_id=str(upload_id),
                source_detail={"row": 1},
            ),
        )

        # 누락 탐지
        detection = detect_missing_evidence(db, deal_id)
        assert detection.total_targets_checked == 1
        assert detection.missing_count == 0
        assert detection.coverage_percentage == 100.0

    def test_unmapped_accounts_warning(self, db: Session):
        """미매핑 계정 존재 시 tie-out WARNING."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)

        _insert_tb(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출액", Decimal("10000000")),
                ("9999", "XYZABC알수없는", Decimal("500")),
            ],
        )

        # 매출만 매핑+승인
        create_data = [
            AccountMappingCreate(
                source_account_code="1001",
                source_account_name="매출액",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                match_score=Decimal("100.00"),
                algorithm="exact",
                affected_amount=Decimal("10000000"),
            ),
        ]
        saved = save_mappings(db, deal_id, create_data)
        from app.services.mapping.coa_mapper import approve_mapping as approve_fn

        approve_fn(db, saved[0], "golden_tester")

        is_result, _bs_result = validate_tie_out(db, deal_id, snapshot_id)
        # 미매핑 존재 → WARNING
        assert is_result.unmapped_account_count > 0

    def test_is_bs_both_present(self, db: Session):
        """IS + BS 양쪽 모두 매핑 시 Tie-out 결과 2개 생성."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)

        _insert_tb(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출액", Decimal("10000000")),
                ("4001", "현금및현금성자산", Decimal("5000000")),
            ],
        )

        create_data = [
            AccountMappingCreate(
                source_account_code="1001",
                source_account_name="매출액",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                match_score=Decimal("100.00"),
                algorithm="exact",
                affected_amount=Decimal("10000000"),
            ),
            AccountMappingCreate(
                source_account_code="4001",
                source_account_name="현금및현금성자산",
                target_line_item_code="BS-CASH-001",
                confidence=MappingConfidence.HIGH,
                match_score=Decimal("100.00"),
                algorithm="exact",
                affected_amount=Decimal("5000000"),
            ),
        ]
        saved = save_mappings(db, deal_id, create_data)
        from app.services.mapping.coa_mapper import approve_mapping as approve_fn

        for m in saved:
            approve_fn(db, m, "golden_tester")

        is_result, bs_result = validate_tie_out(db, deal_id, snapshot_id)
        assert is_result.statement_type == FinancialStatement.IS
        assert bs_result.statement_type == FinancialStatement.BS
        assert is_result.tb_total == Decimal("10000000")
        assert bs_result.tb_total == Decimal("5000000")
