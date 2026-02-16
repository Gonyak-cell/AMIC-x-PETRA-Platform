"""Mapping API 통합 테스트 — FDD-302, FDD-303."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
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
from app.models.upload import IngestionStatus, UploadFile
from app.utils.hashing import hash_json

# ── Helpers ───────────────────────────────────────────────


def _setup_deal(db: Session) -> uuid.UUID:
    deal = Deal(
        name="API Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.flush()
    return deal.id


def _seed_line_items(db: Session) -> None:
    items = [
        (
            "IS-REV-001",
            "Revenue",
            "매출액",
            "REVENUE",
            "IS",
            100,
            ["매출", "수익", "revenue", "sales"],
        ),
        (
            "IS-COGS-001",
            "COGS",
            "매출원가",
            "COGS",
            "IS",
            200,
            ["매출원가", "원가", "COGS"],
        ),
        ("BS-CASH-001", "Cash", "현금", "CASH", "BS", 1000, ["현금", "cash"]),
    ]
    for code, en, ko, cat, stmt, order, kw in items:
        db.add(
            StandardLineItem(
                code=code,
                name_en=en,
                name_ko=ko,
                category=LineItemCategory(cat),
                statement_type=FinancialStatement(stmt),
                display_order=order,
                is_subtotal=False,
                keywords=kw,
            )
        )
    db.commit()


def _seed_tb_data(db: Session, deal_id: uuid.UUID) -> None:
    uf = UploadFile(
        deal_id=deal_id,
        original_filename="tb.xlsx",
        stored_path="/tmp/tb.xlsx",
        file_hash="apitesthash",
        file_size_bytes=1024,
        status=IngestionStatus.COMPLETED,
    )
    db.add(uf)
    db.flush()

    entries = [
        ("1001", "매출액", Decimal("5000000")),
        ("2001", "매출원가", Decimal("3000000")),
        ("3001", "현금", Decimal("2000000")),
    ]
    for i, (code, name, balance) in enumerate(entries, 1):
        db.add(
            JournalEntry(
                upload_file_id=uf.id,
                deal_id=deal_id,
                source_type="TB",
                row_number=i,
                account_code=code,
                account_name=name,
                balance=balance,
            )
        )
    db.commit()


# ── Standard Line Items API ───────────────────────────────


class TestStandardLineItemsAPI:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/v1/standard-line-items")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_items(self, client: TestClient, db: Session):
        _seed_line_items(db)
        resp = client.get("/api/v1/standard-line-items")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["code"] == "IS-REV-001"


# ── Mapping Suggest API ───────────────────────────────────


class TestSuggestAPI:
    def test_suggest_no_deal(self, client: TestClient):
        resp = client.post(f"/api/v1/deals/{uuid.uuid4()}/mappings/suggest")
        assert resp.status_code == 404

    def test_suggest_no_line_items(self, client: TestClient, db: Session):
        deal_id = _setup_deal(db)
        resp = client.post(f"/api/v1/deals/{deal_id}/mappings/suggest")
        assert resp.status_code == 400
        assert "Standard line items" in resp.json()["detail"]

    def test_suggest_no_tb_data(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)
        resp = client.post(f"/api/v1/deals/{deal_id}/mappings/suggest")
        assert resp.status_code == 400
        assert "No TB data" in resp.json()["detail"]

    def test_suggest_success(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)
        _seed_tb_data(db, deal_id)

        resp = client.post(f"/api/v1/deals/{deal_id}/mappings/suggest")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

        # 매출액 → exact match
        revenue = next(s for s in data if s["source_account_code"] == "1001")
        assert revenue["suggested_target_code"] == "IS-REV-001"
        assert revenue["confidence"] == "HIGH"
        assert revenue["algorithm"] == "exact"


# ── Mapping CRUD API ──────────────────────────────────────


class TestMappingCrudAPI:
    def test_create_bulk(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        body = {
            "mappings": [
                {
                    "source_account_code": "1001",
                    "source_account_name": "매출액",
                    "target_line_item_code": "IS-REV-001",
                    "confidence": "HIGH",
                    "match_score": "100.00",
                    "algorithm": "exact",
                    "affected_amount": "5000000",
                },
            ]
        }
        resp = client.post(f"/api/v1/deals/{deal_id}/mappings", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source_account_code"] == "1001"
        assert data[0]["status"] == "PROPOSED"

    def test_list_mappings(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        # 매핑 생성
        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code="1001",
                source_account_name="매출",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.PROPOSED,
                affected_amount=Decimal("5000000"),
            )
        )
        db.commit()

        resp = client.get(f"/api/v1/deals/{deal_id}/mappings")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_mappings_filter_status(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code="1001",
                source_account_name="매출",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.PROPOSED,
                affected_amount=Decimal("5000000"),
            )
        )
        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code="2001",
                source_account_name="원가",
                target_line_item_code="IS-COGS-001",
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.APPROVED,
                affected_amount=Decimal("3000000"),
                approved_by="test",
            )
        )
        db.commit()

        resp = client.get(f"/api/v1/deals/{deal_id}/mappings?status=APPROVED")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["status"] == "APPROVED"

    def test_get_mapping(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code="1001",
            source_account_name="매출",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.PROPOSED,
            affected_amount=Decimal("5000000"),
        )
        db.add(mapping)
        db.flush()
        mapping_id = mapping.id
        db.commit()

        resp = client.get(f"/api/v1/deals/{deal_id}/mappings/{mapping_id}")
        assert resp.status_code == 200
        assert resp.json()["source_account_code"] == "1001"

    def test_get_mapping_not_found(self, client: TestClient, db: Session):
        deal_id = _setup_deal(db)
        resp = client.get(f"/api/v1/deals/{deal_id}/mappings/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_update_mapping(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code="1001",
            source_account_name="매출",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.PROPOSED,
            affected_amount=Decimal("5000000"),
        )
        db.add(mapping)
        db.flush()
        mapping_id = mapping.id
        db.commit()

        resp = client.put(
            f"/api/v1/deals/{deal_id}/mappings/{mapping_id}",
            json={"target_line_item_code": "IS-COGS-001"},
        )
        assert resp.status_code == 200
        assert resp.json()["target_line_item_code"] == "IS-COGS-001"


# ── Approve API ───────────────────────────────────────────


class TestApproveAPI:
    def test_approve_single(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code="1001",
            source_account_name="매출",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.PROPOSED,
            affected_amount=Decimal("5000000"),
        )
        db.add(mapping)
        db.flush()
        mapping_id = mapping.id
        db.commit()

        resp = client.post(
            f"/api/v1/deals/{deal_id}/mappings/{mapping_id}/approve",
            json={"approved_by": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"
        assert resp.json()["approved_by"] == "admin"

    def test_approve_already_approved(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code="1001",
            source_account_name="매출",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.APPROVED,
            affected_amount=Decimal("5000000"),
            approved_by="test",
        )
        db.add(mapping)
        db.flush()
        mapping_id = mapping.id
        db.commit()

        resp = client.post(
            f"/api/v1/deals/{deal_id}/mappings/{mapping_id}/approve",
            json={"approved_by": "admin"},
        )
        assert resp.status_code == 400

    def test_approve_all_proposed(self, client: TestClient, db: Session):
        _seed_line_items(db)
        deal_id = _setup_deal(db)

        for i in range(3):
            db.add(
                AccountMapping(
                    deal_id=deal_id,
                    source_account_code=f"A{i}",
                    source_account_name=f"Account {i}",
                    target_line_item_code="IS-REV-001",
                    confidence=MappingConfidence.HIGH,
                    status=MappingStatus.PROPOSED,
                    affected_amount=Decimal("1000"),
                )
            )
        db.commit()

        resp = client.post(
            f"/api/v1/deals/{deal_id}/mappings/approve-all",
            json={"approved_by": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert all(m["status"] == "APPROVED" for m in data)

    def test_approve_all_no_proposed(self, client: TestClient, db: Session):
        deal_id = _setup_deal(db)
        resp = client.post(
            f"/api/v1/deals/{deal_id}/mappings/approve-all",
            json={"approved_by": "admin"},
        )
        assert resp.status_code == 400


# ── Tie-out API ───────────────────────────────────────────


class TestTieOutAPI:
    def _setup_full(self, db: Session) -> tuple[uuid.UUID, uuid.UUID]:
        _seed_line_items(db)
        deal_id = _setup_deal(db)
        _seed_tb_data(db, deal_id)

        definition = DealDefinition(
            deal_id=deal_id,
            version=1,
            definition_data={"test": True},
            status=DefinitionStatus.APPROVED,
            hash=hash_json({"test": True}),
        )
        db.add(definition)
        db.flush()

        snapshot = DealSnapshot(
            deal_id=deal_id,
            definition_version_id=definition.id,
            engine_version="0.1.0",
            input_hash="test123",
            status=SnapshotStatus.RUNNING,
        )
        db.add(snapshot)
        db.flush()

        # APPROVED 매핑
        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code="1001",
                source_account_name="매출액",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.APPROVED,
                affected_amount=Decimal("5000000"),
                approved_by="test",
            )
        )
        db.commit()

        return deal_id, snapshot.id

    def test_run_tie_out(self, client: TestClient, db: Session):
        deal_id, snapshot_id = self._setup_full(db)

        resp = client.post(
            f"/api/v1/deals/{deal_id}/tie-out/validate",
            json={"snapshot_id": str(snapshot_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # IS + BS

        statement_types = {r["statement_type"] for r in data}
        assert "IS" in statement_types
        assert "BS" in statement_types

    def test_list_tie_out_results(self, client: TestClient, db: Session):
        deal_id, snapshot_id = self._setup_full(db)

        # 먼저 실행
        client.post(
            f"/api/v1/deals/{deal_id}/tie-out/validate",
            json={"snapshot_id": str(snapshot_id)},
        )

        resp = client.get(f"/api/v1/deals/{deal_id}/tie-out")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_tie_out_not_found_deal(self, client: TestClient):
        resp = client.post(
            f"/api/v1/deals/{uuid.uuid4()}/tie-out/validate",
            json={"snapshot_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
