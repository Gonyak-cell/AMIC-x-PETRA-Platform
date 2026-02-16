"""QoE API 통합 테스트 — FDD-501/502/503."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import Deal, DealDefinition, DealSnapshot, DealStatus, DealType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.seeds.standard_coa_v1 import seed_standard_line_items
from app.utils.hashing import hash_json


@pytest.fixture(autouse=True)
def seed_coa(db: Session):
    """모든 QoE API 테스트에서 표준 라인아이템 시드."""
    seed_standard_line_items(db)


def _setup_deal(db: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """테스트용 Deal + Definition + Snapshot + UploadFile 생성.

    Returns: (deal_id, snapshot_id, upload_file_id)
    """
    deal = Deal(
        name="QoE API Test Deal",
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
        file_hash="abc123api",
        file_size_bytes=1024,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()

    definition_data = {"qoe": {"formula": "standard"}}
    defn = DealDefinition(
        deal_id=deal.id,
        version=1,
        definition_data=definition_data,
        hash=hash_json(definition_data),
    )
    db.add(defn)
    db.flush()

    snapshot = DealSnapshot(
        deal_id=deal.id,
        definition_version_id=defn.id,
        engine_version="0.1.0",
        input_hash=hash_json({"def": defn.hash}),
        status="RUNNING",
    )
    db.add(snapshot)
    db.flush()
    db.commit()

    return deal.id, snapshot.id, upload.id


def _add_tb_and_mappings(
    db: Session,
    deal_id: uuid.UUID,
    upload_file_id: uuid.UUID,
    accounts: list[tuple[str, str, str, str]],
) -> None:
    """TB JournalEntry + APPROVED AccountMapping 생성.

    accounts: [(code, name, balance, target_line_item_code), ...]
    """
    for code, name, balance, target_code in accounts:
        je = JournalEntry(
            deal_id=deal_id,
            upload_file_id=upload_file_id,
            source_type="TB",
            account_code=code,
            account_name=name,
            balance=Decimal(balance),
            row_number=1,
        )
        db.add(je)

        mapping = AccountMapping(
            deal_id=deal_id,
            source_account_code=code,
            source_account_name=name,
            target_line_item_code=target_code,
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.APPROVED,
            match_score=Decimal("100.00"),
            algorithm="exact",
            affected_amount=Decimal(balance),
            approved_by="test",
        )
        db.add(mapping)

    db.commit()


class TestQoECalculateAPI:
    """POST /deals/{id}/qoe/calculate."""

    def test_calculate_qoe_success(self, client, db: Session):
        """QoE 계산 성공."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        _add_tb_and_mappings(
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

        resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert Decimal(data["reported_ebitda"]) == Decimal("20000000.0000")
        assert Decimal(data["balance_check_error"]) == Decimal("0.0000")
        assert data["status"] == "DRAFT"

    def test_calculate_qoe_no_mappings_error(self, client, db: Session):
        """매핑 없으면 에러."""
        deal_id, snapshot_id, _ = _setup_deal(db)
        resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )
        assert resp.status_code == 422

    def test_calculate_qoe_deal_not_found(self, client, db: Session):
        """존재하지 않는 Deal."""
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/deals/{fake_id}/qoe/calculate",
            json={"snapshot_id": fake_id},
        )
        assert resp.status_code == 404


class TestQoEListAPI:
    """GET /deals/{id}/qoe."""

    def test_list_qoe_empty(self, client, db: Session):
        """QoE 결과 없으면 빈 리스트."""
        deal_id, _, _ = _setup_deal(db)
        resp = client.get(f"/api/v1/deals/{deal_id}/qoe")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_qoe_after_calculation(self, client, db: Session):
        """계산 후 결과 조회."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        _add_tb_and_mappings(
            db,
            deal_id,
            upload_id,
            [
                ("4100", "매출액", "-50000000", "IS-REV-001"),
                ("5100", "매출원가", "30000000", "IS-COGS-001"),
            ],
        )

        # Calculate
        client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )

        # List
        resp = client.get(f"/api/v1/deals/{deal_id}/qoe")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "adjustments" in data[0]


class TestQoEBridgeAPI:
    """GET /deals/{id}/qoe/{qoe_id}/bridge."""

    def test_get_bridge(self, client, db: Session):
        """Bridge 요약 조회."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        _add_tb_and_mappings(
            db,
            deal_id,
            upload_id,
            [
                ("4100", "매출액", "-50000000", "IS-REV-001"),
                ("5100", "매출원가", "30000000", "IS-COGS-001"),
            ],
        )

        # Calculate
        calc_resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )
        qoe_id = calc_resp.json()["id"]

        # Get bridge
        resp = client.get(f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/bridge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_balanced"] is True
        assert Decimal(data["balance_check_error"]) == Decimal("0")


class TestAdjustmentAPI:
    """POST/PUT /deals/{id}/qoe/{qoe_id}/adjustments."""

    def test_add_manual_adjustment(self, client, db: Session):
        """수동 조정항목 추가."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        _add_tb_and_mappings(
            db,
            deal_id,
            upload_id,
            [
                ("4100", "매출액", "-50000000", "IS-REV-001"),
                ("5100", "매출원가", "30000000", "IS-COGS-001"),
            ],
        )

        calc_resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )
        qoe_id = calc_resp.json()["id"]

        resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/adjustments",
            json={
                "category": "NON_RECURRING",
                "description": "일회성 소송비용",
                "amount": "5000000",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["detection_method"] == "manual"
        assert data["status"] == "PROPOSED"

    def test_approve_adjustment(self, client, db: Session):
        """조정항목 승인."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        _add_tb_and_mappings(
            db,
            deal_id,
            upload_id,
            [
                ("4100", "매출액", "-50000000", "IS-REV-001"),
                ("5100", "매출원가", "30000000", "IS-COGS-001"),
            ],
        )

        calc_resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )
        qoe_id = calc_resp.json()["id"]

        # Add manual
        adj_resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/adjustments",
            json={
                "category": "NON_RECURRING",
                "description": "소송비용",
                "amount": "5000000",
            },
        )
        adj_id = adj_resp.json()["id"]

        # Approve
        resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/adjustments/{adj_id}/approve",
            json={"approved_by": "partner"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"
        assert resp.json()["approved_by"] == "partner"

    def test_recalculate_bridge_after_approve(self, client, db: Session):
        """조정 승인 후 Bridge 재계산."""
        deal_id, snapshot_id, upload_id = _setup_deal(db)
        _add_tb_and_mappings(
            db,
            deal_id,
            upload_id,
            [
                ("4100", "매출액", "-50000000", "IS-REV-001"),
                ("5100", "매출원가", "30000000", "IS-COGS-001"),
            ],
        )

        calc_resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/calculate",
            json={"snapshot_id": str(snapshot_id)},
        )
        qoe_id = calc_resp.json()["id"]
        original_adjusted = Decimal(calc_resp.json()["adjusted_ebitda"])

        # Add and approve
        adj_resp = client.post(
            f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/adjustments",
            json={
                "category": "NON_RECURRING",
                "description": "소송비용",
                "amount": "5000000",
            },
        )
        adj_id = adj_resp.json()["id"]
        client.post(
            f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/adjustments/{adj_id}/approve",
            json={"approved_by": "partner"},
        )

        # Recalculate
        resp = client.post(f"/api/v1/deals/{deal_id}/qoe/{qoe_id}/recalculate")
        assert resp.status_code == 200
        data = resp.json()
        new_adjusted = Decimal(data["adjusted_ebitda"])
        assert new_adjusted == original_adjusted + Decimal("5000000")
        assert Decimal(data["balance_check_error"]) == Decimal("0")
