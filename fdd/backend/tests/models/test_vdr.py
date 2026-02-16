"""Tests for VdrFolder model (Sprint 13)."""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.deal import Deal, DealType
from app.models.vdr import VdrFolder, VdrFolderType


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


class TestVdrFolderModel:
    def test_create_vdr_folder(self, db: Session) -> None:
        """Create a VDR folder and verify all fields are persisted."""
        deal = _create_deal(db)

        folder = VdrFolder(
            deal_id=deal.id,
            name="Financial Statements",
            folder_type=VdrFolderType.FINANCIAL_STATEMENTS,
            order_index=0,
            is_required=True,
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)

        assert folder.id is not None
        assert isinstance(folder.id, uuid.UUID)
        assert folder.deal_id == deal.id
        assert folder.name == "Financial Statements"
        assert folder.folder_type == VdrFolderType.FINANCIAL_STATEMENTS
        assert folder.order_index == 0
        assert folder.is_required is True
        assert folder.parent_id is None
        assert folder.created_at is not None
        assert folder.updated_at is not None

    def test_vdr_folder_hierarchy(self, db: Session) -> None:
        """Create parent and child folders, verify children relationship."""
        deal = _create_deal(db)

        parent = VdrFolder(
            deal_id=deal.id,
            name="Financial Statements",
            folder_type=VdrFolderType.FINANCIAL_STATEMENTS,
            order_index=0,
            is_required=True,
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)

        child = VdrFolder(
            deal_id=deal.id,
            parent_id=parent.id,
            name="2024 BS",
            folder_type=VdrFolderType.CUSTOM,
            order_index=0,
            is_required=False,
        )
        db.add(child)
        db.commit()
        db.refresh(parent)
        db.refresh(child)

        assert child.parent_id == parent.id
        assert len(parent.children) == 1
        assert parent.children[0].id == child.id
        assert child.parent.id == parent.id

    def test_vdr_folder_cascade_delete(self, db: Session) -> None:
        """Deleting a deal cascades to its VDR folders."""
        deal = _create_deal(db)
        deal_id = deal.id

        folder = VdrFolder(
            deal_id=deal.id,
            name="Accounts Receivable",
            folder_type=VdrFolderType.ACCOUNTS_RECEIVABLE,
            order_index=1,
            is_required=False,
        )
        db.add(folder)
        db.commit()
        folder_id = folder.id

        # Delete the deal
        db.delete(deal)
        db.commit()

        # Verify folder is gone
        assert db.get(VdrFolder, folder_id) is None
        assert db.get(Deal, deal_id) is None
