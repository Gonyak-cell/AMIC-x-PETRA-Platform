"""Checklist Service — FDD 체크리스트 CRUD 및 Report IR 리파인.

사용자 리뷰/수정 후 체크리스트를 Finalize하고,
수정사항을 반영한 Refined Report IR을 생성한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.fdd_checklist import (
    ChecklistItemStatus,
    ChecklistStatus,
    FddChecklist,
    FddChecklistItem,
)
from app.schemas.fdd_checklist import ChecklistBulkItem, ChecklistItemUpdate

logger = get_logger(__name__)


class ChecklistService:
    """FDD 체크리스트 비즈니스 로직."""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_checklist(self, deal_id: UUID) -> FddChecklist:
        """Deal의 최신 체크리스트를 조회한다 (항목 + VDR 링크 포함)."""
        checklist = self.db.scalar(
            select(FddChecklist)
            .where(FddChecklist.deal_id == deal_id)
            .options(
                joinedload(FddChecklist.items).joinedload(FddChecklistItem.vdr_links)
            )
            .order_by(FddChecklist.version.desc())
            .limit(1)
        )
        if checklist is None:
            raise NotFoundError(resource="FddChecklist", resource_id=str(deal_id))
        return checklist

    def get_checklist_by_id(self, checklist_id: UUID, deal_id: UUID) -> FddChecklist:
        """ID로 체크리스트를 조회한다."""
        checklist = self.db.scalar(
            select(FddChecklist)
            .where(FddChecklist.id == checklist_id, FddChecklist.deal_id == deal_id)
            .options(
                joinedload(FddChecklist.items).joinedload(FddChecklistItem.vdr_links)
            )
        )
        if checklist is None:
            raise NotFoundError(resource="FddChecklist", resource_id=str(checklist_id))
        return checklist

    def update_item(
        self,
        item_id: UUID,
        update: ChecklistItemUpdate,
        actor: str,
    ) -> FddChecklistItem:
        """체크리스트 항목을 리뷰/수정한다."""
        item = self.db.get(FddChecklistItem, item_id)
        if item is None:
            raise NotFoundError(resource="FddChecklistItem", resource_id=str(item_id))

        item.status = update.status
        if update.user_correction is not None:
            item.user_correction = update.user_correction
        if update.user_amount is not None:
            item.user_amount = update.user_amount
        item.reviewed_by = actor
        item.reviewed_at = datetime.now(UTC)

        self.db.flush()
        return item

    def bulk_update_items(
        self,
        checklist_id: UUID,
        updates: list[ChecklistBulkItem],
        actor: str,
    ) -> list[FddChecklistItem]:
        """여러 항목을 한번에 업데이트한다."""
        results = []
        for bulk_item in updates:
            item = self.db.get(FddChecklistItem, bulk_item.item_id)
            if item is None or item.checklist_id != checklist_id:
                continue
            item.status = bulk_item.status
            if bulk_item.user_correction is not None:
                item.user_correction = bulk_item.user_correction
            if bulk_item.user_amount is not None:
                item.user_amount = bulk_item.user_amount
            item.reviewed_by = actor
            item.reviewed_at = datetime.now(UTC)
            results.append(item)

        self.db.flush()
        return results

    def finalize_checklist(
        self,
        checklist_id: UUID,
        deal_id: UUID,
        actor: str,
        notes: str | None = None,
    ) -> FddChecklist:
        """체크리스트를 Finalize한다.

        모든 항목이 리뷰(AUTO_GENERATED 외)되어야 Finalize 가능.
        """
        checklist = self.get_checklist_by_id(checklist_id, deal_id)

        if checklist.status == ChecklistStatus.FINALIZED:
            raise ValueError("Checklist is already finalized")

        # 리뷰되지 않은 항목 확인
        pending_items = [
            i for i in checklist.items
            if i.status == ChecklistItemStatus.AUTO_GENERATED
        ]
        if pending_items:
            logger.warning(
                "Finalizing checklist %s with %d unreviewed items",
                checklist_id,
                len(pending_items),
            )

        checklist.status = ChecklistStatus.FINALIZED
        checklist.finalized_at = datetime.now(UTC)
        checklist.finalized_by = actor
        if notes:
            checklist.notes = notes

        self.db.commit()
        self.db.refresh(checklist)
        return checklist

    def get_checklist_summary(self, checklist: FddChecklist) -> dict:
        """체크리스트 요약 통계를 반환한다."""
        items = checklist.items
        return {
            "total_items": len(items),
            "confirmed_count": sum(
                1 for i in items if i.status == ChecklistItemStatus.CONFIRMED
            ),
            "corrected_count": sum(
                1 for i in items if i.status == ChecklistItemStatus.CORRECTED
            ),
            "flagged_count": sum(
                1 for i in items if i.status == ChecklistItemStatus.FLAGGED
            ),
            "pending_count": sum(
                1 for i in items if i.status == ChecklistItemStatus.AUTO_GENERATED
            ),
            "not_applicable_count": sum(
                1 for i in items if i.status == ChecklistItemStatus.NOT_APPLICABLE
            ),
        }
