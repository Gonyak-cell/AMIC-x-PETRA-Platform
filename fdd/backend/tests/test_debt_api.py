"""Net Debt API 통합 테스트 — FDD-701/702/703/704."""

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


def _seed_debt_data(db):
    """BS 매핑 + TB 데이터를 DB에 시드한다 (Debt/Cash 포함)."""
    deal = Deal(
        name="Debt Test Deal",
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
        hash="test-hash-debt",
    )
    db.add(defn)
    db.flush()

    snapshot = DealSnapshot(
        deal_id=deal.id,
        definition_version_id=defn.id,
        engine_version="0.1.0",
        input_hash="test-input-debt",
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
        ("BS-CASH-001", "Cash", "현금", "CASH", "BS", 1000),
        (
            "BS-CASH-002",
            "Short-term Financial Assets",
            "단기금융상품",
            "CASH",
            "BS",
            1010,
        ),
        ("BS-DEBT-001", "Short-term Borrowings", "단기차입금", "DEBT", "BS", 2300),
        ("BS-DEBT-002", "Long-term Borrowings", "장기차입금", "DEBT", "BS", 2310),
        (
            "BS-LEASE-001",
            "Lease Liabilities (Current)",
            "리스부채(유동)",
            "LEASE_LIABILITIES",
            "BS",
            2400,
        ),
        ("BS-ACC-004", "Advance from Customers", "선수금", "ACCRUALS", "BS", 2130),
        ("BS-AR-001", "Accounts Receivable", "매출채권", "AR", "BS", 1100),
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
        ("1000", "현금및현금성자산", Decimal("10000000"), "BS-CASH-001"),
        ("1010", "단기금융상품", Decimal("5000000"), "BS-CASH-002"),
        ("2300", "단기차입금", Decimal("-3000000"), "BS-DEBT-001"),
        ("2310", "장기차입금", Decimal("-7000000"), "BS-DEBT-002"),
        ("2400", "리스부채(유동)", Decimal("-2000000"), "BS-LEASE-001"),
        ("2130", "선수금", Decimal("-1500000"), "BS-ACC-004"),
        ("1100", "매출채권", Decimal("8000000"), "BS-AR-001"),
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


class TestNetDebtAPI:
    def test_calculate_net_debt(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        assert resp.status_code == 201
        data = resp.json()
        # Gross Debt = 3M + 7M = 10M
        assert Decimal(data["gross_debt"]) == Decimal("10000000.0000")
        # Cash = 10M + 5M = 15M
        assert Decimal(data["cash_and_equivalents"]) == Decimal("15000000.0000")
        # Net Debt = 10M - 15M = -5M
        assert Decimal(data["net_debt"]) == Decimal("-5000000.0000")
        assert data["status"] == "DRAFT"

    def test_calculate_with_lease(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={
                "snapshot_id": str(snapshot.id),
                "include_lease_liabilities": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        # Debt-like = lease 2M
        assert Decimal(data["debt_like_total"]) == Decimal("2000000.0000")
        assert data["include_lease_liabilities"] is True

    def test_calculate_with_deferred_revenue(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={
                "snapshot_id": str(snapshot.id),
                "include_deferred_revenue": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        # 선수금 1.5M
        assert Decimal(data["debt_like_total"]) == Decimal("1500000.0000")

    def test_list_debt(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        resp = client.get(f"/api/v1/deals/{deal.id}/debt")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_debt(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        calc_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/deals/{deal.id}/debt/{calc_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == calc_id

    def test_debt_bridge(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        calc_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/deals/{deal.id}/debt/{calc_id}/bridge")
        assert resp.status_code == 200
        data = resp.json()
        assert "gross_debt" in data
        assert "adjusted_net_debt" in data

    def test_add_manual_debt_item(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        calc_id = create_resp.json()["id"]
        resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/{calc_id}/items",
            json={
                "item_type": "DEBT_LIKE",
                "description": "Contingent liability",
                "amount": "500000",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["detection_method"] == "manual"
        assert resp.json()["status"] == "PROPOSED"

    def test_approve_debt_item(self, db, client):
        deal, snapshot = _seed_debt_data(db)
        create_resp = client.post(
            f"/api/v1/deals/{deal.id}/debt/calculate",
            json={"snapshot_id": str(snapshot.id)},
        )
        calc_id = create_resp.json()["id"]
        items = create_resp.json()["items"]
        if items:
            item_id = items[0]["id"]
            resp = client.post(
                f"/api/v1/deals/{deal.id}/debt/{calc_id}/items/{item_id}/approve",
                json={"approved_by": "analyst"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "APPROVED"

    def test_deal_not_found(self, db, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/deals/{fake_id}/debt")
        assert resp.status_code == 404
