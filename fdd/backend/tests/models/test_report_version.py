"""Tests for ReportVersion model (Sprint 13)."""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.deal import Deal, DealType
from app.models.report_version import ReportStatus, ReportVersion


def _create_deal(db: Session) -> Deal:
    """Helper to create a minimal deal for testing."""
    deal = Deal(
        name="Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2024, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


class TestReportVersionModel:
    def test_create_report_version(self, db: Session) -> None:
        """Create a report version and verify all fields."""
        deal = _create_deal(db)

        rv = ReportVersion(
            deal_id=deal.id,
            version=1,
            status=ReportStatus.DRAFT,
            file_format="pptx",
            options={"include_charts": True},
            notes="Initial draft",
            created_by="analyst@autofdd.dev",
        )
        db.add(rv)
        db.commit()
        db.refresh(rv)

        assert rv.id is not None
        assert isinstance(rv.id, uuid.UUID)
        assert rv.deal_id == deal.id
        assert rv.version == 1
        assert rv.status == ReportStatus.DRAFT
        assert rv.file_path is None
        assert rv.file_format == "pptx"
        assert rv.options == {"include_charts": True}
        assert rv.notes == "Initial draft"
        assert rv.created_by == "analyst@autofdd.dev"
        assert rv.created_at is not None
        assert rv.finalized_at is None

    def test_report_version_status_transition(self, db: Session) -> None:
        """Create a DRAFT report version and transition to FINAL."""
        deal = _create_deal(db)

        rv = ReportVersion(
            deal_id=deal.id,
            version=1,
            status=ReportStatus.DRAFT,
            file_format="pptx",
            options={},
            created_by="analyst@autofdd.dev",
        )
        db.add(rv)
        db.commit()
        db.refresh(rv)

        assert rv.status == ReportStatus.DRAFT

        # Transition to FINAL
        rv.status = ReportStatus.FINAL
        rv.file_path = "/reports/deal-1/v1.pptx"
        db.commit()
        db.refresh(rv)

        assert rv.status == ReportStatus.FINAL
        assert rv.file_path == "/reports/deal-1/v1.pptx"
