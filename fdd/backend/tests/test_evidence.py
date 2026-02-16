"""Evidence Ledger + 누락 탐지기 테스트 — FDD-401, FDD-402."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingConfidence, MappingStatus
from app.models.audit import AuditLog
from app.models.deal import Deal, DealType
from app.models.evidence import SourceType
from app.models.standard_line_item import (
    FinancialStatement,
    LineItemCategory,
    StandardLineItem,
)
from app.schemas.evidence import EvidenceLinkCreate
from app.services.evidence.detector import detect_missing_evidence
from app.services.evidence.ledger_service import (
    bulk_create_evidence_links,
    create_evidence_link,
    delete_evidence_link,
    get_evidence_link,
    list_evidence_links,
)

# ── Helpers ───────────────────────────────────────────────


def _make_deal(db: Session) -> uuid.UUID:
    deal = Deal(
        name="Evidence Test Deal",
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


def _make_link_data(target_id: uuid.UUID | None = None) -> EvidenceLinkCreate:
    return EvidenceLinkCreate(
        target_type="account_mapping",
        target_id=target_id or uuid.uuid4(),
        source_type=SourceType.TB,
        source_id="upload-file-abc",
        source_detail={"sheet": "시산표", "row": 5},
        engine_version="0.1.0",
    )


# ── Ledger Service ────────────────────────────────────────


class TestCreateEvidenceLink:
    def test_create_single_link(self, db: Session):
        deal_id = _make_deal(db)
        link_data = _make_link_data()

        link = create_evidence_link(db, deal_id, link_data)

        assert link.id is not None
        assert link.deal_id == deal_id
        assert link.target_type == "account_mapping"
        assert link.source_type == SourceType.TB
        assert link.source_detail == {"sheet": "시산표", "row": 5}

    def test_create_link_creates_audit(self, db: Session):
        deal_id = _make_deal(db)
        link_data = _make_link_data()

        create_evidence_link(db, deal_id, link_data)

        logs = list(
            db.scalars(select(AuditLog).where(AuditLog.entity_type == "evidence_link"))
        )
        assert len(logs) == 1
        assert logs[0].action.value == "CREATE"


class TestBulkCreateEvidenceLinks:
    def test_bulk_create(self, db: Session):
        deal_id = _make_deal(db)
        links_data = [_make_link_data() for _ in range(5)]

        created = bulk_create_evidence_links(db, deal_id, links_data)
        assert len(created) == 5

    def test_bulk_create_audit_logs(self, db: Session):
        deal_id = _make_deal(db)
        links_data = [_make_link_data() for _ in range(3)]

        bulk_create_evidence_links(db, deal_id, links_data)

        logs = list(
            db.scalars(select(AuditLog).where(AuditLog.entity_type == "evidence_link"))
        )
        assert len(logs) == 3


class TestListEvidenceLinks:
    def test_list_by_deal(self, db: Session):
        deal_id = _make_deal(db)
        other_deal_id = _make_deal(db)

        create_evidence_link(db, deal_id, _make_link_data())
        create_evidence_link(db, deal_id, _make_link_data())
        create_evidence_link(db, other_deal_id, _make_link_data())

        links = list_evidence_links(db, deal_id)
        assert len(links) == 2

    def test_filter_by_target_type(self, db: Session):
        deal_id = _make_deal(db)

        link1 = _make_link_data()
        create_evidence_link(db, deal_id, link1)

        link2 = EvidenceLinkCreate(
            target_type="qoe_adjustment",
            target_id=uuid.uuid4(),
            source_type=SourceType.GL,
            source_id="gl-entry-001",
        )
        create_evidence_link(db, deal_id, link2)

        links = list_evidence_links(db, deal_id, target_type="account_mapping")
        assert len(links) == 1
        assert links[0].target_type == "account_mapping"

    def test_filter_by_source_type(self, db: Session):
        deal_id = _make_deal(db)

        create_evidence_link(db, deal_id, _make_link_data())

        gl_link = EvidenceLinkCreate(
            target_type="account_mapping",
            target_id=uuid.uuid4(),
            source_type=SourceType.GL,
            source_id="gl-001",
        )
        create_evidence_link(db, deal_id, gl_link)

        links = list_evidence_links(db, deal_id, source_type=SourceType.GL)
        assert len(links) == 1
        assert links[0].source_type == SourceType.GL


class TestGetEvidenceLink:
    def test_get_existing(self, db: Session):
        deal_id = _make_deal(db)
        link = create_evidence_link(db, deal_id, _make_link_data())

        found = get_evidence_link(db, link.id)
        assert found is not None
        assert found.id == link.id

    def test_get_nonexistent(self, db: Session):
        found = get_evidence_link(db, uuid.uuid4())
        assert found is None


class TestDeleteEvidenceLink:
    def test_delete(self, db: Session):
        deal_id = _make_deal(db)
        link = create_evidence_link(db, deal_id, _make_link_data())
        link_id = link.id

        delete_evidence_link(db, link)

        assert get_evidence_link(db, link_id) is None


# ── Evidence Missing Detector ─────────────────────────────


class TestDetectMissingEvidence:
    def test_no_mappings_returns_empty(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        result = detect_missing_evidence(db, deal_id)
        assert result.total_targets_checked == 0
        assert result.missing_count == 0
        assert result.coverage_percentage == 100.0

    def test_all_covered(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        # APPROVED 매핑 생성
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

        # Evidence 연결
        create_evidence_link(
            db,
            deal_id,
            EvidenceLinkCreate(
                target_type="account_mapping",
                target_id=mapping.id,
                source_type=SourceType.TB,
                source_id="upload-001",
            ),
        )

        result = detect_missing_evidence(db, deal_id)
        assert result.total_targets_checked == 1
        assert result.missing_count == 0
        assert result.coverage_percentage == 100.0

    def test_missing_evidence_detected(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        # APPROVED 매핑 2개 생성, evidence 없음
        for i in range(2):
            db.add(
                AccountMapping(
                    deal_id=deal_id,
                    source_account_code=f"A{i}",
                    source_account_name=f"Account {i}",
                    target_line_item_code="IS-REV-001",
                    confidence=MappingConfidence.HIGH,
                    status=MappingStatus.APPROVED,
                    affected_amount=Decimal("1000"),
                    approved_by="test",
                )
            )
        db.commit()

        result = detect_missing_evidence(db, deal_id)
        assert result.total_targets_checked == 2
        assert result.missing_count == 2
        assert result.coverage_percentage == 0.0
        assert len(result.missing) == 2

    def test_partial_coverage(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        # 매핑 2개 생성
        m1 = AccountMapping(
            deal_id=deal_id,
            source_account_code="A1",
            source_account_name="매출",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.APPROVED,
            affected_amount=Decimal("1000"),
            approved_by="test",
        )
        m2 = AccountMapping(
            deal_id=deal_id,
            source_account_code="A2",
            source_account_name="원가",
            target_line_item_code="IS-REV-001",
            confidence=MappingConfidence.HIGH,
            status=MappingStatus.APPROVED,
            affected_amount=Decimal("2000"),
            approved_by="test",
        )
        db.add_all([m1, m2])
        db.flush()

        # m1만 evidence 연결
        create_evidence_link(
            db,
            deal_id,
            EvidenceLinkCreate(
                target_type="account_mapping",
                target_id=m1.id,
                source_type=SourceType.TB,
                source_id="upload-001",
            ),
        )

        result = detect_missing_evidence(db, deal_id)
        assert result.total_targets_checked == 2
        assert result.missing_count == 1
        assert result.coverage_percentage == 50.0

    def test_proposed_mappings_skipped(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        # PROPOSED 매핑 (check_approved_only=True이므로 제외)
        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code="A1",
                source_account_name="매출",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.PROPOSED,
                affected_amount=Decimal("1000"),
            )
        )
        db.commit()

        result = detect_missing_evidence(db, deal_id, check_approved_only=True)
        assert result.total_targets_checked == 0

    def test_check_all_mappings(self, db: Session):
        _make_line_items(db)
        deal_id = _make_deal(db)

        db.add(
            AccountMapping(
                deal_id=deal_id,
                source_account_code="A1",
                source_account_name="매출",
                target_line_item_code="IS-REV-001",
                confidence=MappingConfidence.HIGH,
                status=MappingStatus.PROPOSED,
                affected_amount=Decimal("1000"),
            )
        )
        db.commit()

        result = detect_missing_evidence(db, deal_id, check_approved_only=False)
        assert result.total_targets_checked == 1
        assert result.missing_count == 1
