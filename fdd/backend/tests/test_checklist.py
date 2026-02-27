"""Tests for FDD Checklist API endpoints.

체크리스트 CRUD, 항목 리뷰/수정, 일괄 업데이트, Finalize 워크플로우를 검증한다.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealType
from app.models.fdd_checklist import (
    ChecklistCategory,
    ChecklistItemStatus,
    ChecklistSeverity,
    ChecklistStatus,
    FddChecklist,
    FddChecklistItem,
)

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def deal(db: Session) -> Deal:
    """테스트용 Deal 생성."""
    deal = Deal(
        name="Checklist Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def checklist_with_items(db: Session, deal: Deal) -> FddChecklist:
    """18개 항목을 가진 체크리스트 생성."""
    checklist = FddChecklist(
        deal_id=deal.id,
        version=1,
        status=ChecklistStatus.PENDING_REVIEW,
        created_by="test@autofdd.dev",
    )
    db.add(checklist)
    db.flush()

    categories = list(ChecklistCategory)
    for i, category in enumerate(categories):
        item = FddChecklistItem(
            checklist_id=checklist.id,
            category=category,
            order_index=i,
            title=f"Test {category.value}",
            description=f"Description for {category.value}",
            auto_finding=f"Auto finding for {category.value}",
            auto_amount=Decimal("1000000") * (i + 1),
            severity=ChecklistSeverity.HIGH if i < 6 else ChecklistSeverity.MEDIUM,
        )
        db.add(item)

    db.commit()
    db.refresh(checklist)
    return checklist


# ── GET /deals/{deal_id}/checklist ──────────────────────────────────────


class TestGetChecklist:
    def test_get_latest_checklist(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        resp = client.get(f"/api/v1/deals/{deal.id}/checklist")
        assert resp.status_code == 200

        data = resp.json()
        assert data["version"] == 1
        assert data["status"] == "PENDING_REVIEW"
        assert data["total_items"] == 18
        assert data["pending_count"] == 18  # 모두 AUTO_GENERATED
        assert data["confirmed_count"] == 0
        assert len(data["items"]) == 18

    def test_get_checklist_not_found(self, client: TestClient, deal: Deal):
        resp = client.get(f"/api/v1/deals/{deal.id}/checklist")
        assert resp.status_code == 404

    def test_get_checklist_by_id(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        checklist_id = str(checklist_with_items.id)
        resp = client.get(f"/api/v1/deals/{deal.id}/checklist/{checklist_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == checklist_id

    def test_items_have_correct_structure(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        resp = client.get(f"/api/v1/deals/{deal.id}/checklist")
        item = resp.json()["items"][0]

        assert "id" in item
        assert "category" in item
        assert "title" in item
        assert "description" in item
        assert "auto_finding" in item
        assert "auto_amount" in item
        assert "status" in item
        assert "severity" in item
        assert "vdr_links" in item
        assert item["status"] == "AUTO_GENERATED"


# ── PUT /deals/{deal_id}/checklist/items/{item_id} ─────────────────────


class TestUpdateChecklistItem:
    def test_confirm_item(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        item_id = str(checklist_with_items.items[0].id)
        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/items/{item_id}",
            json={"status": "CONFIRMED"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CONFIRMED"
        assert data["reviewed_by"] is not None

    def test_correct_item_with_user_values(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        item_id = str(checklist_with_items.items[0].id)
        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/items/{item_id}",
            json={
                "status": "CORRECTED",
                "user_correction": "수정된 매출인식 기준 적용",
                "user_amount": "5000000",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CORRECTED"
        assert data["user_correction"] == "수정된 매출인식 기준 적용"
        assert data["user_amount"].startswith("5000000")

    def test_flag_item(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        item_id = str(checklist_with_items.items[0].id)
        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/items/{item_id}",
            json={"status": "FLAGGED"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "FLAGGED"

    def test_mark_not_applicable(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        item_id = str(checklist_with_items.items[0].id)
        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/items/{item_id}",
            json={"status": "NOT_APPLICABLE"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "NOT_APPLICABLE"

    def test_update_nonexistent_item(self, client: TestClient, deal: Deal):
        fake_id = str(uuid.uuid4())
        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/items/{fake_id}",
            json={"status": "CONFIRMED"},
        )
        assert resp.status_code == 404


# ── PUT /deals/{deal_id}/checklist/{id}/bulk-update ────────────────────


class TestBulkUpdate:
    def test_bulk_update_items(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        checklist_id = str(checklist_with_items.id)
        items = checklist_with_items.items[:3]

        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/{checklist_id}/bulk-update",
            json={
                "items": [
                    {"item_id": str(items[0].id), "status": "CONFIRMED"},
                    {
                        "item_id": str(items[1].id),
                        "status": "CORRECTED",
                        "user_correction": "Bulk corrected",
                        "user_amount": "999999",
                    },
                    {"item_id": str(items[2].id), "status": "FLAGGED"},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        statuses = {d["status"] for d in data}
        assert statuses == {"CONFIRMED", "CORRECTED", "FLAGGED"}

    def test_bulk_update_empty_list(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        checklist_id = str(checklist_with_items.id)
        resp = client.put(
            f"/api/v1/deals/{deal.id}/checklist/{checklist_id}/bulk-update",
            json={"items": []},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ── POST /deals/{deal_id}/checklist/{id}/finalize ──────────────────────


class TestFinalizeChecklist:
    def test_finalize_checklist(
        self,
        client: TestClient,
        db: Session,
        deal: Deal,
        checklist_with_items: FddChecklist,
    ):
        # 먼저 모든 항목을 CONFIRMED로 변경
        for item in checklist_with_items.items:
            item.status = ChecklistItemStatus.CONFIRMED
        db.commit()

        checklist_id = str(checklist_with_items.id)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/checklist/{checklist_id}/finalize",
            json={"notes": "최종 확정"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FINALIZED"
        assert data["finalized_at"] is not None

    def test_finalize_with_pending_items_still_succeeds(
        self, client: TestClient, deal: Deal, checklist_with_items: FddChecklist
    ):
        """미검수 항목이 있어도 Finalize는 경고만 하고 진행한다."""
        checklist_id = str(checklist_with_items.id)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/checklist/{checklist_id}/finalize",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "FINALIZED"

    def test_finalize_already_finalized_fails(
        self,
        client: TestClient,
        db: Session,
        deal: Deal,
        checklist_with_items: FddChecklist,
    ):
        checklist_with_items.status = ChecklistStatus.FINALIZED
        db.commit()

        checklist_id = str(checklist_with_items.id)
        resp = client.post(
            f"/api/v1/deals/{deal.id}/checklist/{checklist_id}/finalize",
            json={},
        )
        assert resp.status_code == 400
        assert "already finalized" in resp.json()["detail"]


# ── Summary Statistics ──────────────────────────────────────────────────


class TestChecklistSummary:
    def test_summary_counts_after_mixed_review(
        self,
        client: TestClient,
        db: Session,
        deal: Deal,
        checklist_with_items: FddChecklist,
    ):
        items = checklist_with_items.items
        # 6 confirmed, 4 corrected, 3 flagged, 2 not_applicable, 3 pending
        for i, item in enumerate(items):
            if i < 6:
                item.status = ChecklistItemStatus.CONFIRMED
            elif i < 10:
                item.status = ChecklistItemStatus.CORRECTED
            elif i < 13:
                item.status = ChecklistItemStatus.FLAGGED
            elif i < 15:
                item.status = ChecklistItemStatus.NOT_APPLICABLE
            # else: remain AUTO_GENERATED
        db.commit()

        resp = client.get(f"/api/v1/deals/{deal.id}/checklist")
        data = resp.json()
        assert data["total_items"] == 18
        assert data["confirmed_count"] == 6
        assert data["corrected_count"] == 4
        assert data["flagged_count"] == 3
        assert data["pending_count"] == 3


# ── Version Management ──────────────────────────────────────────────────


class TestChecklistVersioning:
    def test_multiple_versions_returns_latest(
        self, client: TestClient, db: Session, deal: Deal
    ):
        # v1
        cl1 = FddChecklist(
            deal_id=deal.id,
            version=1,
            status=ChecklistStatus.FINALIZED,
            created_by="test@autofdd.dev",
        )
        db.add(cl1)
        db.flush()
        db.add(
            FddChecklistItem(
                checklist_id=cl1.id,
                category=ChecklistCategory.REVENUE_RECOGNITION,
                order_index=0,
                title="V1 Revenue",
                description="V1",
            )
        )

        # v2
        cl2 = FddChecklist(
            deal_id=deal.id,
            version=2,
            status=ChecklistStatus.PENDING_REVIEW,
            created_by="test@autofdd.dev",
        )
        db.add(cl2)
        db.flush()
        db.add(
            FddChecklistItem(
                checklist_id=cl2.id,
                category=ChecklistCategory.REVENUE_RECOGNITION,
                order_index=0,
                title="V2 Revenue",
                description="V2",
            )
        )
        db.commit()

        resp = client.get(f"/api/v1/deals/{deal.id}/checklist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 2
        assert data["items"][0]["title"] == "V2 Revenue"
