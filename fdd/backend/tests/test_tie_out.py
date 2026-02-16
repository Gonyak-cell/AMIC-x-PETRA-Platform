"""Tie-out 검증 서비스 단위 테스트 — FDD-303."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import (
    Deal,
    DealDefinition,
    DealSnapshot,
    DealType,
    DefinitionStatus,
    SnapshotStatus,
)
from app.models.journal_entry import JournalEntry
from app.models.standard_line_item import (
    FinancialStatement,
    LineItemCategory,
    StandardLineItem,
)
from app.models.tie_out import TieOutResult, TieOutStatus
from app.services.mapping.tie_out import (
    _find_top_discrepancies,
    _get_tb_accounts,
    reconstruct_statements,
    validate_tie_out,
)
from app.utils.hashing import hash_json

# ── Fixtures ──────────────────────────────────────────────


def _setup_deal_with_snapshot(db: Session) -> tuple[uuid.UUID, uuid.UUID]:
    """Deal + Definition + Snapshot 생성 → (deal_id, snapshot_id)."""
    deal = Deal(
        name="TieOut Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.flush()

    definition = DealDefinition(
        deal_id=deal.id,
        version=1,
        definition_data={"test": True},
        status=DefinitionStatus.APPROVED,
        hash=hash_json({"test": True}),
    )
    db.add(definition)
    db.flush()

    snapshot = DealSnapshot(
        deal_id=deal.id,
        definition_version_id=definition.id,
        engine_version="0.1.0",
        input_hash="abc123",
        status=SnapshotStatus.RUNNING,
    )
    db.add(snapshot)
    db.flush()

    return deal.id, snapshot.id


def _seed_line_items(db: Session) -> None:
    """테스트용 표준 라인아이템."""
    items = [
        ("IS-REV-001", "Revenue", "매출액", "REVENUE", "IS", 100),
        ("IS-COGS-001", "COGS", "매출원가", "COGS", "IS", 200),
        ("BS-CASH-001", "Cash", "현금", "CASH", "BS", 1000),
        ("BS-AP-001", "Accounts Payable", "매입채무", "AP", "BS", 2000),
    ]
    for code, en, ko, cat, stmt, order in items:
        db.add(
            StandardLineItem(
                code=code,
                name_en=en,
                name_ko=ko,
                category=LineItemCategory(cat),
                statement_type=FinancialStatement(stmt),
                display_order=order,
                is_subtotal=False,
            )
        )
    db.commit()


def _seed_tb_data(
    db: Session,
    deal_id: uuid.UUID,
    upload_file_id: uuid.UUID,
    accounts: list[tuple[str, str, Decimal]],
) -> None:
    """TB 데이터를 journal_entry에 삽입."""
    for i, (code, name, balance) in enumerate(accounts, 1):
        db.add(
            JournalEntry(
                upload_file_id=upload_file_id,
                deal_id=deal_id,
                source_type="TB",
                row_number=i,
                account_code=code,
                account_name=name,
                balance=balance,
            )
        )
    db.commit()


def _create_upload_file(db: Session, deal_id: uuid.UUID) -> uuid.UUID:
    """테스트용 UploadFile stub 생성."""
    from app.models.upload import IngestionStatus, UploadFile

    uf = UploadFile(
        deal_id=deal_id,
        original_filename="test.xlsx",
        stored_path="/tmp/test.xlsx",
        file_hash="testhash",
        file_size_bytes=1024,
        status=IngestionStatus.COMPLETED,
    )
    db.add(uf)
    db.flush()
    return uf.id


def _create_approved_mappings(
    db: Session,
    deal_id: uuid.UUID,
    mappings: list[tuple[str, str, str, Decimal]],
) -> None:
    """APPROVED 매핑 생성. (source_code, source_name, target_code, amount)."""
    for code, name, target, amount in mappings:
        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code=code,
                source_account_name=name,
                target_line_item_code=target,
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.APPROVED,
                affected_amount=amount,
                approved_by="test",
            )
        )
    db.commit()


# ── _get_tb_accounts ──────────────────────────────────────


class TestGetTBAccounts:
    def test_returns_account_balances(self, db: Session):
        deal_id, _ = _setup_deal_with_snapshot(db)
        upload_id = _create_upload_file(db, deal_id)
        _seed_tb_data(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "현금", Decimal("1000000")),
                ("2001", "매입채무", Decimal("-500000")),
            ],
        )

        tb_map = _get_tb_accounts(db, deal_id)
        assert tb_map["1001"] == Decimal("1000000")
        assert tb_map["2001"] == Decimal("-500000")

    def test_empty_tb(self, db: Session):
        deal_id, _ = _setup_deal_with_snapshot(db)
        tb_map = _get_tb_accounts(db, deal_id)
        assert len(tb_map) == 0

    def test_duplicate_codes_summed(self, db: Session):
        deal_id, _ = _setup_deal_with_snapshot(db)
        upload_id = _create_upload_file(db, deal_id)
        _seed_tb_data(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "현금", Decimal("1000000")),
                ("1001", "현금(2)", Decimal("500000")),
            ],
        )

        tb_map = _get_tb_accounts(db, deal_id)
        assert tb_map["1001"] == Decimal("1500000")


# ── reconstruct_statements ────────────────────────────────


class TestReconstructStatements:
    def test_is_bs_separation(self, db: Session):
        _seed_line_items(db)
        deal_id, _ = _setup_deal_with_snapshot(db)
        upload_id = _create_upload_file(db, deal_id)
        _seed_tb_data(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출", Decimal("5000000")),
                ("2001", "원가", Decimal("3000000")),
                ("3001", "현금", Decimal("2000000")),
            ],
        )
        _create_approved_mappings(
            db,
            deal_id,
            [
                ("1001", "매출", "IS-REV-001", Decimal("5000000")),
                ("2001", "원가", "IS-COGS-001", Decimal("3000000")),
                ("3001", "현금", "BS-CASH-001", Decimal("2000000")),
            ],
        )

        is_totals, bs_totals = reconstruct_statements(db, deal_id)

        assert "IS-REV-001" in is_totals
        assert is_totals["IS-REV-001"] == Decimal("5000000")
        assert "IS-COGS-001" in is_totals
        assert "BS-CASH-001" in bs_totals
        assert bs_totals["BS-CASH-001"] == Decimal("2000000")

    def test_empty_mappings(self, db: Session):
        _seed_line_items(db)
        deal_id, _ = _setup_deal_with_snapshot(db)

        is_totals, bs_totals = reconstruct_statements(db, deal_id)
        assert len(is_totals) == 0
        assert len(bs_totals) == 0


# ── _find_top_discrepancies ──────────────────────────────


class TestFindTopDiscrepancies:
    def test_sorted_by_abs_amount(self, db: Session):
        _seed_line_items(db)
        from sqlalchemy import select

        li_map = {li.code: li for li in db.scalars(select(StandardLineItem)).all()}
        totals = {
            "IS-REV-001": Decimal("5000000"),
            "IS-COGS-001": Decimal("-3000000"),
            "BS-CASH-001": Decimal("100"),
        }
        result = _find_top_discrepancies(totals, li_map, limit=10)
        assert len(result) == 3
        assert result[0]["code"] == "IS-REV-001"  # largest abs
        assert result[1]["code"] == "IS-COGS-001"

    def test_limit_respected(self, db: Session):
        _seed_line_items(db)
        from sqlalchemy import select

        li_map = {li.code: li for li in db.scalars(select(StandardLineItem)).all()}
        totals = {"IS-REV-001": Decimal("100")}
        result = _find_top_discrepancies(totals, li_map, limit=0)
        assert len(result) == 0


# ── validate_tie_out ──────────────────────────────────────


class TestValidateTieOut:
    def test_perfect_tie_out_pass(self, db: Session):
        """모든 계정이 매핑되고 합계 일치 → PASS."""
        _seed_line_items(db)
        deal_id, snapshot_id = _setup_deal_with_snapshot(db)
        upload_id = _create_upload_file(db, deal_id)

        _seed_tb_data(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출", Decimal("5000000")),
                ("2001", "현금", Decimal("5000000")),
            ],
        )
        _create_approved_mappings(
            db,
            deal_id,
            [
                ("1001", "매출", "IS-REV-001", Decimal("5000000")),
                ("2001", "현금", "BS-CASH-001", Decimal("5000000")),
            ],
        )

        is_result, bs_result = validate_tie_out(db, deal_id, snapshot_id)

        assert is_result.status == TieOutStatus.PASS
        assert bs_result.status == TieOutStatus.PASS
        assert is_result.variance == Decimal("0")
        assert bs_result.variance == Decimal("0")

    def test_unmapped_accounts_warning(self, db: Session):
        """미매핑 계정 존재 → WARNING."""
        _seed_line_items(db)
        deal_id, snapshot_id = _setup_deal_with_snapshot(db)
        upload_id = _create_upload_file(db, deal_id)

        _seed_tb_data(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출", Decimal("5000000")),
                ("9999", "미매핑계정", Decimal("100")),
            ],
        )
        _create_approved_mappings(
            db,
            deal_id,
            [
                ("1001", "매출", "IS-REV-001", Decimal("5000000")),
            ],
        )

        is_result, _bs_result = validate_tie_out(db, deal_id, snapshot_id)
        # 미매핑 존재하면 PASS → WARNING으로 변경됨
        assert is_result.unmapped_account_count > 0

    def test_tie_out_creates_db_records(self, db: Session):
        """Tie-out 결과가 DB에 저장된다."""
        _seed_line_items(db)
        deal_id, snapshot_id = _setup_deal_with_snapshot(db)
        upload_id = _create_upload_file(db, deal_id)

        _seed_tb_data(
            db,
            deal_id,
            upload_id,
            [
                ("1001", "매출", Decimal("1000")),
            ],
        )
        _create_approved_mappings(
            db,
            deal_id,
            [
                ("1001", "매출", "IS-REV-001", Decimal("1000")),
            ],
        )

        validate_tie_out(db, deal_id, snapshot_id)

        from sqlalchemy import select

        results = list(
            db.scalars(select(TieOutResult).where(TieOutResult.deal_id == deal_id))
        )
        assert len(results) == 2  # IS + BS

    def test_empty_data_zero_variance(self, db: Session):
        """데이터 없으면 variance 0, PASS."""
        _seed_line_items(db)
        deal_id, snapshot_id = _setup_deal_with_snapshot(db)

        is_result, bs_result = validate_tie_out(db, deal_id, snapshot_id)
        assert is_result.variance == Decimal("0")
        assert bs_result.variance == Decimal("0")
        assert is_result.variance_percentage == Decimal("0")
