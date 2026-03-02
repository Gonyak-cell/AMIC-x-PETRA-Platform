"""FM Checklist Service — 재무모델 체크리스트 CRUD + Finalize.

FDD의 ChecklistService 패턴을 따른다.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import FMChecklistItemStatus, FMChecklistStatus
from app.models.financial_model import FMChecklist, FMChecklistItem
from app.schemas.financial_model import FMChecklistBulkItem, FMChecklistItemUpdate

logger = logging.getLogger(__name__)


class FMChecklistService:
    """재무모델 체크리스트 비즈니스 로직."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_checklist(self, financial_model_id: UUID) -> FMChecklist:
        """재무모델의 체크리스트를 조회한다 (항목 포함)."""
        stmt = (
            select(FMChecklist)
            .where(FMChecklist.financial_model_id == financial_model_id)
            .options(joinedload(FMChecklist.items))
            .order_by(FMChecklist.version.desc())
            .limit(1)
        )
        checklist = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if checklist is None:
            raise DocumentNotFoundError(f"FM Checklist for model {financial_model_id}")
        return checklist

    async def get_checklist_by_id(self, checklist_id: UUID) -> FMChecklist:
        """ID로 체크리스트를 조회한다."""
        stmt = select(FMChecklist).where(FMChecklist.id == checklist_id).options(joinedload(FMChecklist.items))
        checklist = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if checklist is None:
            raise DocumentNotFoundError(f"FM Checklist {checklist_id}")
        return checklist

    async def update_item(
        self,
        item_id: UUID,
        update: FMChecklistItemUpdate,
        actor: str,
    ) -> FMChecklistItem:
        """체크리스트 항목을 리뷰/수정한다."""
        item = await self.db.get(FMChecklistItem, item_id)
        if item is None:
            raise DocumentNotFoundError(f"FM Checklist Item {item_id}")

        item.status = update.status
        if update.user_correction is not None:
            item.user_correction = update.user_correction
        if update.user_value is not None:
            item.user_value = update.user_value
        item.reviewed_by = actor
        item.reviewed_at = datetime.now(UTC)

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def bulk_update_items(
        self,
        checklist_id: UUID,
        updates: list[FMChecklistBulkItem],
        actor: str,
    ) -> list[FMChecklistItem]:
        """여러 항목을 한번에 업데이트한다."""
        # N+1 방지: 단일 IN 쿼리로 일괄 로딩
        item_ids = [bulk.item_id for bulk in updates]
        stmt = select(FMChecklistItem).where(FMChecklistItem.id.in_(item_ids))
        rows = (await self.db.execute(stmt)).scalars().all()
        items_by_id = {item.id: item for item in rows}

        results: list[FMChecklistItem] = []
        skipped: list[str] = []
        for bulk in updates:
            item = items_by_id.get(bulk.item_id)
            if item is None:
                skipped.append(f"{bulk.item_id} (not found)")
                continue
            if item.checklist_id != checklist_id:
                skipped.append(f"{bulk.item_id} (checklist mismatch)")
                continue
            item.status = bulk.status
            if bulk.user_correction is not None:
                item.user_correction = bulk.user_correction
            if bulk.user_value is not None:
                item.user_value = bulk.user_value
            item.reviewed_by = actor
            item.reviewed_at = datetime.now(UTC)
            results.append(item)

        if skipped:
            logger.warning(
                "bulk_update_items: %d items skipped — %s",
                len(skipped),
                ", ".join(skipped),
            )

        await self.db.flush()
        # N+1 방지: 개별 refresh() 대신 단일 IN 쿼리로 일괄 재로딩
        if results:
            refreshed_ids = [item.id for item in results]
            refresh_stmt = select(FMChecklistItem).where(FMChecklistItem.id.in_(refreshed_ids))
            refreshed_rows = (await self.db.execute(refresh_stmt)).scalars().all()
            refreshed_map = {r.id: r for r in refreshed_rows}
            results = [refreshed_map[iid] for iid in refreshed_ids if iid in refreshed_map]
        return results

    async def finalize_checklist(
        self,
        checklist_id: UUID,
        actor: str,
        notes: str | None = None,
    ) -> FMChecklist:
        """체크리스트를 Finalize한다.

        모든 항목이 리뷰(AUTO_GENERATED 외)되어야 Finalize 가능.
        """
        checklist = await self.get_checklist_by_id(checklist_id)

        if checklist.status == FMChecklistStatus.FINALIZED:
            raise ValueError("Checklist is already finalized")

        pending_items = [i for i in checklist.items if i.status == FMChecklistItemStatus.AUTO_GENERATED]
        if pending_items:
            logger.warning(
                "Finalizing FM checklist %s with %d unreviewed items",
                checklist_id,
                len(pending_items),
            )

        checklist.status = FMChecklistStatus.FINALIZED
        checklist.finalized_at = datetime.now(UTC)
        checklist.finalized_by = actor
        if notes:
            checklist.notes = notes

        await self.db.flush()
        await self.db.refresh(checklist)
        return checklist

    @staticmethod
    def compute_summary(checklist: FMChecklist) -> dict:
        """체크리스트 요약 통계를 반환한다."""
        items = checklist.items
        return {
            "total_items": len(items),
            "confirmed_count": sum(1 for i in items if i.status == FMChecklistItemStatus.CONFIRMED),
            "corrected_count": sum(1 for i in items if i.status == FMChecklistItemStatus.CORRECTED),
            "flagged_count": sum(1 for i in items if i.status == FMChecklistItemStatus.FLAGGED),
            "pending_count": sum(1 for i in items if i.status == FMChecklistItemStatus.AUTO_GENERATED),
            "not_applicable_count": sum(1 for i in items if i.status == FMChecklistItemStatus.NOT_APPLICABLE),
        }
