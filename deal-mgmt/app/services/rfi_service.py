"""RFI 핵심 CRUD + 워크플로우 서비스."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    AuditAction,
    RFICategory,
    RFIItemPriority,
    RFIItemStatus,
    RFISourceType,
    RFIStatus,
)
from app.models.rfi import RFI
from app.models.rfi_item import RFIItem
from app.schemas.rfi import (
    RFICategorySummary,
    RFICreate,
    RFIItemCreate,
    RFIItemRespondInput,
    RFIItemReviewInput,
    RFIItemUpdate,
    RFISummary,
    RFIUpdate,
)
from app.services import audit_service


# ── RFI CRUD ───────────────────────────────────────────────


async def list_rfis(
    db: AsyncSession,
    txn_id: uuid.UUID,
    *,
    rfi_status: str | None = None,
    round_number: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[RFI]:
    q = select(RFI).where(RFI.transaction_id == txn_id)
    if rfi_status:
        q = q.where(RFI.status == rfi_status)
    if round_number is not None:
        q = q.where(RFI.round_number == round_number)
    q = q.order_by(RFI.round_number, RFI.created_at).offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_rfi(db: AsyncSession, txn_id: uuid.UUID, rfi_id: uuid.UUID) -> RFI:
    q = (
        select(RFI)
        .options(selectinload(RFI.items).selectinload(RFIItem.checklist_mappings))
        .where(RFI.id == rfi_id, RFI.transaction_id == txn_id)
    )
    rfi = (await db.execute(q)).scalar_one_or_none()
    if rfi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFI를 찾을 수 없습니다")
    return rfi


async def create_rfi(
    db: AsyncSession,
    txn_id: uuid.UUID,
    body: RFICreate,
    actor_email: str | None = None,
) -> RFI:
    rfi = RFI(transaction_id=txn_id, created_by_email=actor_email, **body.model_dump())
    db.add(rfi)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="RFI",
        entity_id=rfi.id,
        action=AuditAction.CREATE,
        actor_email=actor_email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(rfi)
    return rfi


async def update_rfi(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    body: RFIUpdate,
    actor_email: str | None = None,
) -> RFI:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(rfi, k, v)
    await audit_service.record(
        db,
        entity_type="RFI",
        entity_id=rfi.id,
        action=AuditAction.UPDATE,
        actor_email=actor_email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(rfi)
    return rfi


async def delete_rfi(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    actor_email: str | None = None,
) -> None:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    if rfi.status != RFIStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DRAFT 상태의 RFI만 삭제할 수 있습니다",
        )
    await audit_service.record(
        db, entity_type="RFI", entity_id=rfi.id, action=AuditAction.DELETE, actor_email=actor_email
    )
    await db.delete(rfi)
    await db.commit()


# ── RFI 워크플로우 ─────────────────────────────────────────


async def send_rfi(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    actor_email: str | None = None,
) -> RFI:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    if rfi.status != RFIStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DRAFT 상태에서만 발송 가능합니다")
    if rfi.total_items == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="질문이 없는 RFI는 발송할 수 없습니다")
    rfi.status = RFIStatus.SENT
    rfi.sent_at = datetime.now(timezone.utc)
    await audit_service.record(
        db, entity_type="RFI", entity_id=rfi.id, action=AuditAction.UPDATE,
        actor_email=actor_email, new_value={"status": "SENT"},
    )
    await db.commit()
    await db.refresh(rfi)
    return rfi


async def close_rfi(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    actor_email: str | None = None,
) -> RFI:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    # BE-WF-01: DRAFT/CLOSED/CANCELLED 상태에서는 마감 불가
    if rfi.status in (RFIStatus.DRAFT, RFIStatus.CLOSED, RFIStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"현재 상태({rfi.status.value})에서는 마감할 수 없습니다",
        )
    rfi.status = RFIStatus.CLOSED
    rfi.closed_at = datetime.now(timezone.utc)
    await audit_service.record(
        db, entity_type="RFI", entity_id=rfi.id, action=AuditAction.UPDATE,
        actor_email=actor_email, new_value={"status": "CLOSED"},
    )
    await db.commit()
    await db.refresh(rfi)
    return rfi


async def extend_deadline(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    new_due_date: str,
    actor_email: str | None = None,
) -> RFI:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    # BE-WF-05: 과거 날짜 및 기존 마감일 이전 검증
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if new_due_date < today_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="과거 날짜로 마감일을 연장할 수 없습니다",
        )
    if rfi.due_date and new_due_date <= rfi.due_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="기존 마감일 이후로만 연장할 수 있습니다",
        )
    old_date = rfi.due_date
    rfi.due_date = new_due_date
    await audit_service.record(
        db, entity_type="RFI", entity_id=rfi.id, action=AuditAction.UPDATE,
        actor_email=actor_email,
        old_value={"due_date": old_date},
        new_value={"due_date": new_due_date},
    )
    await db.commit()
    await db.refresh(rfi)
    return rfi


# ── RFI Item CRUD ──────────────────────────────────────────


async def list_rfi_items(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    *,
    category: str | None = None,
    item_status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RFIItem]:
    q = select(RFIItem).where(RFIItem.rfi_id == rfi_id, RFIItem.transaction_id == txn_id)
    if category:
        q = q.where(RFIItem.category == category)
    if item_status:
        q = q.where(RFIItem.status == item_status)
    if priority:
        q = q.where(RFIItem.priority == priority)
    q = q.order_by(RFIItem.question_number).offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def add_rfi_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    body: RFIItemCreate,
    actor_email: str | None = None,
) -> RFIItem:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    next_num = await _next_question_number(db, rfi_id)
    item = RFIItem(
        rfi_id=rfi_id,
        transaction_id=txn_id,
        question_number=next_num,
        **body.model_dump(),
    )
    db.add(item)
    await db.flush()
    await _update_rfi_counts(db, rfi)
    await audit_service.record(
        db, entity_type="RFIItem", entity_id=item.id, action=AuditAction.CREATE,
        actor_email=actor_email, new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(item)
    return item


async def batch_add_items(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    items: list[RFIItemCreate],
    actor_email: str | None = None,
) -> list[RFIItem]:
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    next_num = await _next_question_number(db, rfi_id)
    created = []
    for i, body in enumerate(items):
        item = RFIItem(
            rfi_id=rfi_id,
            transaction_id=txn_id,
            question_number=next_num + i,
            **body.model_dump(),
        )
        db.add(item)
        created.append(item)
    await db.flush()
    await _update_rfi_counts(db, rfi)
    await audit_service.record(
        db, entity_type="RFI", entity_id=rfi.id, action=AuditAction.UPDATE,
        actor_email=actor_email, new_value={"batch_items_added": len(created)},
    )
    await db.commit()
    # BE-PERF-03: 단일 IN 쿼리로 refresh 대체
    ids = [item.id for item in created]
    refreshed_q = select(RFIItem).where(RFIItem.id.in_(ids)).order_by(RFIItem.question_number)
    refreshed = list((await db.execute(refreshed_q)).scalars().all())
    return refreshed


async def update_rfi_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RFIItemUpdate,
    actor_email: str | None = None,
) -> RFIItem:
    item = await _get_rfi_item(db, txn_id, rfi_id, item_id)
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    await audit_service.record(
        db, entity_type="RFIItem", entity_id=item.id, action=AuditAction.UPDATE,
        actor_email=actor_email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(item)
    return item


async def delete_rfi_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    actor_email: str | None = None,
) -> None:
    item = await _get_rfi_item(db, txn_id, rfi_id, item_id)
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    await audit_service.record(
        db, entity_type="RFIItem", entity_id=item.id, action=AuditAction.DELETE, actor_email=actor_email
    )
    await db.delete(item)
    await db.flush()
    await _update_rfi_counts(db, rfi)
    await db.commit()


# ── 응답 / 검토 ───────────────────────────────────────────


async def respond_to_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RFIItemRespondInput,
    responder_email: str | None = None,
) -> RFIItem:
    item = await _get_rfi_item(db, txn_id, rfi_id, item_id)
    # BE-WF-02: ACCEPTED/NOT_APPLICABLE 상태 아이템 재응답 차단
    if item.status in (RFIItemStatus.ACCEPTED, RFIItemStatus.NOT_APPLICABLE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"현재 상태({item.status.value})에서는 응답할 수 없습니다",
        )
    item.response = body.response
    item.response_documents = body.response_documents
    item.responded_at = datetime.now(timezone.utc)
    item.responded_by = responder_email
    item.status = RFIItemStatus.RESPONDED
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    await _update_rfi_counts(db, rfi)
    await _auto_transition_rfi_status(db, rfi)
    await audit_service.record(
        db, entity_type="RFIItem", entity_id=item.id, action=AuditAction.UPDATE,
        actor_email=responder_email, new_value={"status": "RESPONDED", "response": body.response[:500]},
    )
    await db.commit()
    await db.refresh(item)
    return item


async def review_item(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RFIItemReviewInput,
    reviewer_email: str | None = None,
) -> RFIItem:
    item = await _get_rfi_item(db, txn_id, rfi_id, item_id)
    # BE-WF-03: RESPONDED 또는 CLARIFICATION_NEEDED 상태에서만 리뷰 가능
    if item.status not in (RFIItemStatus.RESPONDED, RFIItemStatus.CLARIFICATION_NEEDED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"현재 상태({item.status.value})에서는 리뷰할 수 없습니다. 응답 완료 후 리뷰 가능합니다",
        )
    item.status = RFIItemStatus(body.status)
    item.reviewer_comment = body.reviewer_comment
    item.reviewer_email = reviewer_email
    if body.follow_up_question:
        item.follow_up_question = body.follow_up_question
    rfi = await _get_rfi_simple(db, txn_id, rfi_id)
    await _update_rfi_counts(db, rfi)
    await audit_service.record(
        db, entity_type="RFIItem", entity_id=item.id, action=AuditAction.UPDATE,
        actor_email=reviewer_email, new_value={"status": body.status},
    )
    await db.commit()
    await db.refresh(item)
    return item


# ── Summary ────────────────────────────────────────────────


async def get_rfi_summary(db: AsyncSession, txn_id: uuid.UUID) -> RFISummary:
    rfis = await list_rfis(db, txn_id)
    all_items_q = select(RFIItem).where(RFIItem.transaction_id == txn_id)
    result = await db.execute(all_items_q)
    all_items = list(result.scalars().all())

    total_items = len(all_items)
    responded = sum(1 for i in all_items if i.status in (RFIItemStatus.RESPONDED, RFIItemStatus.ACCEPTED))
    accepted = sum(1 for i in all_items if i.status == RFIItemStatus.ACCEPTED)
    pct = (responded / total_items * 100) if total_items > 0 else 0.0

    # 기한 초과
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    overdue = sum(
        1 for i in all_items
        if i.status == RFIItemStatus.PENDING and i.due_date and i.due_date < now_str
    )

    # 카테고리별
    cat_map: dict[str, dict[str, int]] = {}
    for item in all_items:
        cat = item.category.value
        if cat not in cat_map:
            cat_map[cat] = {"total": 0, "responded": 0, "accepted": 0, "pending": 0}
        cat_map[cat]["total"] += 1
        if item.status in (RFIItemStatus.RESPONDED, RFIItemStatus.ACCEPTED):
            cat_map[cat]["responded"] += 1
        if item.status == RFIItemStatus.ACCEPTED:
            cat_map[cat]["accepted"] += 1
        if item.status == RFIItemStatus.PENDING:
            cat_map[cat]["pending"] += 1

    by_category = [
        RFICategorySummary(category=RFICategory(cat), **counts)
        for cat, counts in cat_map.items()
    ]

    return RFISummary(
        total_rfis=len(rfis),
        total_items=total_items,
        responded_items=responded,
        accepted_items=accepted,
        overall_response_pct=round(pct, 1),
        overdue_items=overdue,
        by_category=by_category,
    )


# ── DD 체크리스트 기반 자동 생성 ───────────────────────────


async def generate_from_dd_checklist(
    db: AsyncSession,
    txn_id: uuid.UUID,
    title: str,
    actor_email: str | None = None,
) -> tuple[RFI, int]:
    """DD 미완료(NOT_STARTED) 항목에서 RFI 자동 생성."""
    from app.models.dd_checklist import DDChecklist
    from app.models.enums import DDChecklistStatus

    q = select(DDChecklist).where(
        DDChecklist.transaction_id == txn_id,
        DDChecklist.status == DDChecklistStatus.NOT_STARTED,
    )
    result = await db.execute(q)
    dd_items = list(result.scalars().all())

    if not dd_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자동 생성할 DD 미완료 항목이 없습니다")

    # 최대 라운드 번호
    max_round_q = select(func.coalesce(func.max(RFI.round_number), 0)).where(RFI.transaction_id == txn_id)
    max_round = (await db.execute(max_round_q)).scalar_one()

    rfi = RFI(
        transaction_id=txn_id,
        round_number=max_round + 1,
        title=title,
        status=RFIStatus.DRAFT,
        created_by_email=actor_email,
    )
    db.add(rfi)
    await db.flush()

    # DD workstream → RFI category 매핑
    ws_category_map = {
        "FDD": RFICategory.FINANCIAL,
        "LDD": RFICategory.LEGAL,
        "TDD": RFICategory.TAX,
        "HRD": RFICategory.HR,
        "ITD": RFICategory.IT,
        "ENV": RFICategory.ENVIRONMENTAL,
    }

    from app.models.rfi_checklist_mapping import RFIChecklistMapping

    for i, dd in enumerate(dd_items):
        ws_prefix = dd.workstream.value.split("_")[0] if dd.workstream else ""
        category = ws_category_map.get(ws_prefix, RFICategory.GENERAL)
        item = RFIItem(
            rfi_id=rfi.id,
            transaction_id=txn_id,
            question_number=i + 1,
            category=category,
            question=dd.title,
            question_detail=dd.description,
            priority=RFIItemPriority.MEDIUM,
            source_type=RFISourceType.DD_CHECKLIST,
            source_ref_id=dd.id,
        )
        db.add(item)
        await db.flush()  # item.id 확보
        # BE-SYNC-01: DD 자동생성 시 매핑 레코드도 함께 생성
        mapping = RFIChecklistMapping(
            rfi_item_id=item.id,
            target_module="DD",
            target_item_id=dd.id,
        )
        db.add(mapping)

    rfi.total_items = len(dd_items)
    await audit_service.record(
        db, entity_type="RFI", entity_id=rfi.id, action=AuditAction.CREATE,
        actor_email=actor_email, new_value={"auto_generated_from": "DD", "items": len(dd_items)},
    )
    await db.commit()
    await db.refresh(rfi)
    return rfi, len(dd_items)


# ── 매핑 조회 ─────────────────────────────────────────────


async def get_item_mappings(
    db: AsyncSession,
    txn_id: uuid.UUID,
    rfi_id: uuid.UUID,
    item_id: uuid.UUID,
) -> list:
    """RFI 아이템의 체크리스트 매핑 목록을 반환한다."""
    from app.models.rfi_checklist_mapping import RFIChecklistMapping

    await _get_rfi_item(db, txn_id, rfi_id, item_id)
    q = select(RFIChecklistMapping).where(RFIChecklistMapping.rfi_item_id == item_id)
    result = await db.execute(q)
    return list(result.scalars().all())


# ── 내부 헬퍼 ──────────────────────────────────────────────


async def _get_rfi_simple(db: AsyncSession, txn_id: uuid.UUID, rfi_id: uuid.UUID) -> RFI:
    q = select(RFI).where(RFI.id == rfi_id, RFI.transaction_id == txn_id)
    rfi = (await db.execute(q)).scalar_one_or_none()
    if rfi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFI를 찾을 수 없습니다")
    return rfi


async def _get_rfi_item(db: AsyncSession, txn_id: uuid.UUID, rfi_id: uuid.UUID, item_id: uuid.UUID) -> RFIItem:
    q = select(RFIItem).where(
        RFIItem.id == item_id, RFIItem.rfi_id == rfi_id, RFIItem.transaction_id == txn_id
    )
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFI 항목을 찾을 수 없습니다")
    return item


async def _next_question_number(db: AsyncSession, rfi_id: uuid.UUID) -> int:
    q = select(func.coalesce(func.max(RFIItem.question_number), 0)).where(RFIItem.rfi_id == rfi_id)
    max_num = (await db.execute(q)).scalar_one()
    return max_num + 1


async def _update_rfi_counts(db: AsyncSession, rfi: RFI) -> None:
    """RFI의 total/responded/accepted 카운트를 재집계한다."""
    q = select(RFIItem).where(RFIItem.rfi_id == rfi.id)
    result = await db.execute(q)
    items = list(result.scalars().all())
    rfi.total_items = len(items)
    rfi.responded_items = sum(
        1 for i in items if i.status in (RFIItemStatus.RESPONDED, RFIItemStatus.ACCEPTED)
    )
    rfi.accepted_items = sum(1 for i in items if i.status == RFIItemStatus.ACCEPTED)


async def _auto_transition_rfi_status(db: AsyncSession, rfi: RFI) -> None:
    """응답률 기반으로 RFI 상태를 자동 전환한다."""
    if rfi.status in (RFIStatus.DRAFT, RFIStatus.CLOSED, RFIStatus.CANCELLED):
        return
    if rfi.total_items == 0:
        return
    if rfi.responded_items >= rfi.total_items:
        rfi.status = RFIStatus.FULLY_RESPONDED
    elif rfi.responded_items > 0:
        rfi.status = RFIStatus.PARTIALLY_RESPONDED
