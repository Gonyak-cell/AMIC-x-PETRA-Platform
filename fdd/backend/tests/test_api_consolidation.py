"""Consolidation API 테스트 — Sprint 16.

연결 분석 API 엔드포인트 통합 테스트.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account_mapping import (
    AccountMapping,
    MappingConfidence,
    MappingStatus,
)
from app.models.deal import Deal, DealStatus, DealType
from app.models.entity import Entity, EntityType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.seeds.standard_coa_v1 import seed_standard_line_items

D = Decimal


@pytest.fixture(autouse=True)
def seed_coa(db: Session):
    """표준 라인아이템 시드."""
    seed_standard_line_items(db)


def _seed_full_data(db: Session) -> str:
    """Deal + 2 Entities + TB + Mappings → deal_id 반환."""
    deal = Deal(
        name="Consolidation API Test",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        status=DealStatus.ACTIVE,
    )
    db.add(deal)
    db.flush()

    target = Entity(
        deal_id=deal.id,
        entity_type=EntityType.TARGET,
        name="Target Co",
        code="TARGET",
        functional_currency="KRW",
        ownership_pct=D("100.0000"),
    )
    sub1 = Entity(
        deal_id=deal.id,
        parent_entity_id=None,
        entity_type=EntityType.SUBSIDIARY,
        name="Sub1 Co",
        code="SUB1",
        functional_currency="KRW",
        ownership_pct=D("80.0000"),
    )
    db.add_all([target, sub1])
    db.flush()
    sub1.parent_entity_id = target.id

    upload = UploadFile(
        deal_id=deal.id,
        original_filename="api_test_tb.xlsx",
        stored_path="/tmp/api_test_tb.xlsx",
        file_hash="apihash",
        file_size_bytes=512,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()

    # TB entries
    db.add_all(
        [
            JournalEntry(
                deal_id=deal.id,
                upload_file_id=upload.id,
                entity_id=target.id,
                source_type="TB",
                row_number=1,
                account_code="4100",
                account_name="매출",
                balance=D("-50000000"),
                currency="KRW",
            ),
            JournalEntry(
                deal_id=deal.id,
                upload_file_id=upload.id,
                entity_id=sub1.id,
                source_type="TB",
                row_number=2,
                account_code="4100",
                account_name="매출",
                balance=D("-20000000"),
                currency="KRW",
            ),
        ]
    )

    # Mappings
    db.add(
        AccountMapping(
            deal_id=deal.id,
            source_account_code="4100",
            source_account_name="매출",
            target_line_item_code="IS-REV-001",
            status=MappingStatus.APPROVED,
            confidence=MappingConfidence.HIGH,
            affected_amount=D("50000000"),
        )
    )

    db.commit()
    return str(deal.id)


class TestRunConsolidationAPI:
    """POST /consolidation/run 테스트."""

    def test_run_success(self, client: TestClient, db: Session, auth_headers):
        """연결 분석 성공 → 200."""
        deal_id = _seed_full_data(db)

        resp = client.post(
            f"/api/v1/deals/{deal_id}/consolidation/run",
            json={},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "consolidated_totals" in data
        assert "entity_subtotals" in data
        assert "eliminations" in data
        assert "minority_interest" in data

    def test_run_with_ic_pairs(self, client: TestClient, db: Session, auth_headers):
        """IC pairs 포함 연결 분석."""
        deal_id = _seed_full_data(db)

        resp = client.post(
            f"/api/v1/deals/{deal_id}/consolidation/run",
            json={
                "ic_pairs": [
                    {
                        "debit_entity": "TARGET",
                        "credit_entity": "SUB1",
                        "category": "REVENUE",
                        "amount": "5000000",
                    }
                ]
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["eliminations"]) == 1
        assert D(data["elimination_total"]) == D("5000000")

    def test_run_deal_not_found(self, client: TestClient, auth_headers):
        """존재하지 않는 딜 → 404."""
        fake_id = str(uuid.uuid4())

        resp = client.post(
            f"/api/v1/deals/{fake_id}/consolidation/run",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_run_no_entities(self, client: TestClient, db: Session, auth_headers):
        """엔티티 없는 딜 → 404."""
        deal = Deal(
            name="Empty Deal",
            deal_type=DealType.COMPLETION_ACCOUNTS,
            base_currency="KRW",
            reference_date=date(2025, 12, 31),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            status=DealStatus.ACTIVE,
        )
        db.add(deal)
        db.commit()

        resp = client.post(
            f"/api/v1/deals/{deal.id}/consolidation/run",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "No active entities" in resp.json()["detail"]


class TestEntitiesSummaryAPI:
    """GET /consolidation/entities-summary 테스트."""

    def test_entities_summary_success(
        self, client: TestClient, db: Session, auth_headers
    ):
        """엔티티 요약 조회 성공."""
        deal_id = _seed_full_data(db)

        resp = client.get(
            f"/api/v1/deals/{deal_id}/consolidation/entities-summary",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        codes = {e["code"] for e in data}
        assert "TARGET" in codes
        assert "SUB1" in codes

    def test_entities_summary_empty(
        self, client: TestClient, db: Session, auth_headers
    ):
        """엔티티 없는 딜 → 빈 목록."""
        deal = Deal(
            name="No Entity Deal",
            deal_type=DealType.COMPLETION_ACCOUNTS,
            base_currency="KRW",
            reference_date=date(2025, 12, 31),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            status=DealStatus.ACTIVE,
        )
        db.add(deal)
        db.commit()

        resp = client.get(
            f"/api/v1/deals/{deal.id}/consolidation/entities-summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []
