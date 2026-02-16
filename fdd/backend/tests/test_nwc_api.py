"""NWC API 통합 테스트 — FDD-601/602/603."""

from datetime import date
from decimal import Decimal

from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import Deal, DealDefinition, DealSnapshot, DealType
from app.models.journal_entry import JournalEntry
from app.models.standard_line_item import (
    FinancialStatement,
    LineItemCategory,
    StandardLineItem,
)
from app.models.upload import UploadFile


def _seed_bs_data(db):
    """BS 매핑 + TB 데이터를 DB에 시드한다."""
    deal = Deal(
        name="NWC Test Deal",
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
        definition_data={"test": True},
        hash="test-hash-nwc",
    )
    db.add(defn)
    db.flush()

    snapshot = DealSnapshot(
        deal_id=deal.id,
        definition_version_id=defn.id,
        engine_version="0.1.0",
        input_hash="test-input-nwc",
    )
    db.add(snapshot)
    db.flush()

    upload = UploadFile(
        deal_id=deal.id,
        original_filename="tb.xlsx",
        stored_path="/tmp/tb.xlsx",
        file_hash="abc123",
        file_size_bytes=1024,
    )
    db.add(upload)
    db.flush()

    # Standard line items (BS)
    bs_items = [
        ("BS-AR-001", "Accounts Receivable", "매출채권", "AR", "BS", 1100),
        ("BS-INV-001", "Inventory", "재고자산", "INVENTORY", "BS", 1200),
        ("BS-AP-001", "Accounts Payable", "매입채무", "AP", "BS", 2000),
        ("BS-ACC-001", "Accrued Expenses", "미지급비용", "ACCRUALS", "BS", 2100),
        ("BS-CASH-001", "Cash", "현금", "CASH", "BS", 1000),
        ("BS-DEBT-001", "Short-term Borrowings", "단기차입금", "DEBT", "BS", 2300),
    ]
    for code, name_en, name_ko, cat, stmt, order in bs_items:
        db.add(
            StandardLineItem(
                code=code,
                name_en=name_en,
                name_ko=name_ko,
                category=LineItemCategory(cat),
                statement_type=FinancialStatement(stmt),
                display_order=order,
                is_subtotal=False,
            )
        )
    db.flush()

    # TB entries + mappings
    tb_data = [
        ("1100", "매출채권", Decimal("5000000"), "BS-AR-001"),
        ("1200", "재고자산", Decimal("8000000"), "BS-INV-001"),
        ("2000", "매입채무", Decimal("-3000000"), "BS-AP-001"),
        ("2100", "미지급비용", Decimal("-2000000"), "BS-ACC-001"),
        ("1000", "현금", Decimal("10000000"), "BS-CASH-001"),
        ("2300", "단기차입금", Decimal("-5000000"), "BS-DEBT-001"),
    ]
    for idx, (acct_code, acct_name, balance, target_code) in enumerate(tb_data):
        entry = JournalEntry(
            deal_id=deal.id,
            upload_file_id=upload.id,
            source_type="TB",
            row_number=idx + 1,
            account_code=acct_code,
            account_name=acct_name,
            balance=balance,
        )
        db.add(entry)

        mapping = AccountMapping(
            deal_id=deal.id,
            source_account_code=acct_code,
            source_account_name=acct_name,
            target_line_item_code=target_code,
            status=MappingStatus.APPROVED,
            confidence=MappingConfidence.HIGH,
            algorithm="manual",
            affected_amount=abs(balance),
        )
        db.add(mapping)

    db.commit()
    return deal, snapshot


class TestNWCAPI:
    def test_calculate_nwc(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        # CA = AR(5M) + INV(8M) = 13M
        assert Decimal(data["total_current_assets"]) == Decimal("13000000.0000")
        # CL = AP(3M) + ACC(2M) = 5M
        assert Decimal(data["total_current_liabilities"]) == Decimal("5000000.0000")
        # NWC = 13M - 5M = 8M
        assert Decimal(data["net_working_capital"]) == Decimal("8000000.0000")
        assert data["engine_version"] == "0.1.0"
        assert data["status"] == "DRAFT"
        assert len(data["line_items"]) == 6  # all 6 BS accounts

    def test_list_nwc(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        resp = client.get(f"/api/v1/deals/{deal.id}/nwc")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_nwc(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        nwc_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/deals/{deal.id}/nwc/{nwc_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == nwc_id

    def test_nwc_summary(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        nwc_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/deals/{deal.id}/nwc/{nwc_id}/summary")
        assert resp.status_code == 200
        data = resp.json()
        # above_line: AR, INV, AP, ACC (4 items)
        assert len(data["above_line_items"]) == 4
        # CASH and DEBT are excluded
        assert data["is_above_target"] is True  # NWC(8M) >= Peg(0 for v1)

    def test_peg_simulation(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        nwc_id = create_resp.json()["id"]
        resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/{nwc_id}/peg-simulate",
            json={"peg_method": "LTM_AVERAGE"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scenarios"]) == 6

    def test_recalculate_peg(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        nwc_id = create_resp.json()["id"]
        resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/{nwc_id}/recalculate-peg",
            json={"peg_method": "CUSTOM", "custom_value": "7000000"},
        )
        assert resp.status_code == 200
        assert resp.json()["peg_method"] == "CUSTOM"

    def test_update_line_item_classification(self, db, client):
        deal, snapshot = _seed_bs_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/nwc/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        nwc_id = create_resp.json()["id"]
        # Find AR item
        items = create_resp.json()["line_items"]
        ar_item = next(i for i in items if i["line_item_category"] == "AR")
        resp = client.put(
            f"/api/v1/deals/{deal.id}/nwc/{nwc_id}/items/{ar_item['id']}",
            json={"classification": "BELOW_LINE"},
        )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "BELOW_LINE"

    def test_deal_not_found(self, db, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/deals/{fake_id}/nwc")
        assert resp.status_code == 404
