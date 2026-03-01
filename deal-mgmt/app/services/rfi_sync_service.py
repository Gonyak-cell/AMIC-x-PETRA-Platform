"""RFI ACCEPTED 응답 → 체크리스트 반영 동기화 서비스."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, RFIItemStatus
from app.models.rfi_checklist_mapping import RFIChecklistMapping
from app.models.rfi_item import RFIItem
from app.services import audit_service


async def sync_accepted_to_checklists(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    actor_email: str | None = None,
) -> int:
    """ACCEPTED 상태의 RFI 아이템 응답을 매핑된 체크리스트에 반영한다.

    현재는 DD 체크리스트만 지원 (같은 DB).
    IM/FDD는 내부 HTTP API를 통해 향후 구현.
    """
    from app.models.dd_checklist import DDChecklist

    q = select(RFIItem).where(
        RFIItem.rfi_id == rfi_id,
        RFIItem.transaction_id == txn_id,
        RFIItem.status == RFIItemStatus.ACCEPTED,
    )
    result = await db.execute(q)
    accepted_items = list(result.scalars().all())

    if not accepted_items:
        return 0

    # 1단계: 모든 매핑을 IN 쿼리 1회로 일괄 조회 (N+1 방지)
    item_ids = [item.id for item in accepted_items]
    all_mappings = list(
        (
            await db.execute(
                select(RFIChecklistMapping).where(
                    RFIChecklistMapping.rfi_item_id.in_(item_ids),
                    RFIChecklistMapping.synced.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )

    # 2단계: DD 타겟 ID를 모아 DDChecklist를 IN 쿼리 1회로 조회
    dd_target_ids = [m.target_item_id for m in all_mappings if m.target_module == "DD" and m.target_item_id]
    dd_map: dict[uuid.UUID, DDChecklist] = {}
    if dd_target_ids:
        dd_result = await db.execute(select(DDChecklist).where(DDChecklist.id.in_(dd_target_ids)))
        dd_map = {d.id: d for d in dd_result.scalars().all()}

    # 3단계: 인메모리에서 매핑 처리 (DB 왕복 0)
    item_map = {item.id: item for item in accepted_items}
    synced_count = 0

    for mapping in all_mappings:
        item = item_map.get(mapping.rfi_item_id)
        if not item or not item.response:
            continue
        if mapping.target_module == "DD" and mapping.target_item_id:
            dd_item = dd_map.get(mapping.target_item_id)
            if dd_item:
                existing = dd_item.notes or ""
                dd_item.notes = f"{existing}\n[RFI 응답] {item.response}".strip()
                mapping.synced = True
                mapping.synced_at = datetime.now(UTC)
                mapping.synced_value = item.response[:500]
                synced_count += 1

        # IM/FDD는 내부 HTTP API 연동 (향후 구현)
        # elif mapping.target_module == "IM": ...
        # elif mapping.target_module == "FDD": ...

    if synced_count > 0:
        await audit_service.record(
            db,
            entity_type="RFI",
            entity_id=rfi_id,
            action=AuditAction.UPDATE,
            actor_email=actor_email,
            new_value={"sync_to_checklists": synced_count},
        )
    await db.commit()

    return synced_count
