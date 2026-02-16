"""Evidence API 통합 테스트 — FDD-401, FDD-402."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.deal import Deal, DealType
from app.models.standard_line_item import (
    FinancialStatement,
    LineItemCategory,
    StandardLineItem,
)

# ── Helpers ───────────────────────────────────────────────


def _make_deal(db: Session) -> uuid.UUID:
    deal = Deal(
        name="Evidence API Test",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.flush()
    return deal.id


def _make_line_items(db: Session) -> None:
    db.add(
        StandardLineItem(
            code="IS-REV-001",
            name_en="Revenue",
            name_ko="매출액",
            category=LineItemCategory.REVENUE,
            statement_type=FinancialStatement.IS,
            display_order=100,
            is_subtotal=False,
        )
    )
    db.commit()


# ── Single Create ─────────────────────────────────────────


class TestCreateEvidenceLinkAPI:
    def test_create_link(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        body = {
            "target_type": "account_mapping",
            "target_id": str(uuid.uuid4()),
            "source_type": "TB",
            "source_id": "upload-001",
            "source_detail": {"sheet": "시산표", "row": 5},
        }
        resp = client.post(f"/api/v1/deals/{deal_id}/evidence-links", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["target_type"] == "account_mapping"
        assert data["source_type"] == "TB"
        assert data["source_detail"]["sheet"] == "시산표"
        assert data["deal_id"] == str(deal_id)

    def test_create_link_deal_not_found(self, client: TestClient):
        body = {
            "target_type": "test",
            "target_id": str(uuid.uuid4()),
            "source_type": "TB",
            "source_id": "x",
        }
        resp = client.post(f"/api/v1/deals/{uuid.uuid4()}/evidence-links", json=body)
        assert resp.status_code == 404


# ── Bulk Create ───────────────────────────────────────────


class TestBulkCreateAPI:
    def test_bulk_create(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        body = {
            "links": [
                {
                    "target_type": "account_mapping",
                    "target_id": str(uuid.uuid4()),
                    "source_type": "TB",
                    "source_id": f"upload-{i}",
                }
                for i in range(3)
            ]
        }
        resp = client.post(f"/api/v1/deals/{deal_id}/evidence-links/bulk", json=body)
        assert resp.status_code == 201
        assert len(resp.json()) == 3

    def test_bulk_create_empty(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        body = {"links": []}
        resp = client.post(f"/api/v1/deals/{deal_id}/evidence-links/bulk", json=body)
        assert resp.status_code == 422  # min_length=1 violation


# ── List ──────────────────────────────────────────────────


class TestListEvidenceLinksAPI:
    def test_list_empty(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_data(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)

        # 2개 생성
        for i in range(2):
            client.post(
                f"/api/v1/deals/{deal_id}/evidence-links",
                json={
                    "target_type": "account_mapping",
                    "target_id": str(uuid.uuid4()),
                    "source_type": "TB",
                    "source_id": f"upload-{i}",
                },
            )

        resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_filter_target_type(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)

        client.post(
            f"/api/v1/deals/{deal_id}/evidence-links",
            json={
                "target_type": "account_mapping",
                "target_id": str(uuid.uuid4()),
                "source_type": "TB",
                "source_id": "upload-1",
            },
        )
        client.post(
            f"/api/v1/deals/{deal_id}/evidence-links",
            json={
                "target_type": "qoe_adjustment",
                "target_id": str(uuid.uuid4()),
                "source_type": "GL",
                "source_id": "gl-001",
            },
        )

        resp = client.get(
            f"/api/v1/deals/{deal_id}/evidence-links",
            params={"target_type": "account_mapping"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ── Get / Delete ──────────────────────────────────────────


class TestGetDeleteAPI:
    def test_get_link(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)

        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/evidence-links",
            json={
                "target_type": "account_mapping",
                "target_id": str(uuid.uuid4()),
                "source_type": "TB",
                "source_id": "upload-1",
            },
        )
        link_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links/{link_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == link_id

    def test_get_link_not_found(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_delete_link(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)

        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/evidence-links",
            json={
                "target_type": "account_mapping",
                "target_id": str(uuid.uuid4()),
                "source_type": "TB",
                "source_id": "upload-1",
            },
        )
        link_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/deals/{deal_id}/evidence-links/{link_id}")
        assert del_resp.status_code == 204

        # 삭제 확인
        get_resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links/{link_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        resp = client.delete(f"/api/v1/deals/{deal_id}/evidence-links/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── Missing Detection API ─────────────────────────────────


class TestMissingDetectionAPI:
    def test_no_mappings(self, client: TestClient, db: Session):
        deal_id = _make_deal(db)
        resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links/missing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_targets_checked"] == 0
        assert data["coverage_percentage"] == 100.0

    def test_with_missing_evidence(self, client: TestClient, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        # APPROVED 매핑 2개 (evidence 없음)
        for i in range(2):
            db.add(
                AccountMapping(
                    deal_id=deal_id,
                    source_account_code=f"A{i}",
                    source_account_name=f"Acct {i}",
                    target_line_item_code="IS-REV-001",
                    confidence=MappingConfidence.HIGH,
                    status=MappingStatus.APPROVED,
                    affected_amount=Decimal("1000"),
                    approved_by="test",
                )
            )
        db.commit()

        resp = client.get(f"/api/v1/deals/{deal_id}/evidence-links/missing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_targets_checked"] == 2
        assert data["missing_count"] == 2
        assert data["coverage_percentage"] == 0.0
        assert len(data["missing"]) == 2

    def test_deal_not_found(self, client: TestClient):
        resp = client.get(f"/api/v1/deals/{uuid.uuid4()}/evidence-links/missing")
        assert resp.status_code == 404
