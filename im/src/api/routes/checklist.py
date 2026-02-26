"""체크리스트 API 엔드포인트.

VDR 기반 IM 생성 워크플로우의 체크리스트 CRUD를 제공한다.

POST /api/v1/documents/from-vdr           — VDR 기반 IM 생성 시작
GET  /api/v1/documents/{id}/checklist     — 체크리스트 전체 조회
GET  /api/v1/documents/{id}/checklist/summary — 카테고리별 완료율
PATCH /api/v1/documents/{id}/checklist/items/{item_id} — 개별 아이템 수정
POST /api/v1/documents/{id}/checklist/items/batch-update — 일괄 수정
POST /api/v1/documents/{id}/checklist/confirm — 확정 → IM 생성 시작
POST /api/v1/documents/{id}/checklist/reparse — VDR 문서 재파싱
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.db.models.document import Document, DocumentStatus
from src.api.db.models.im_checklist import ChecklistStatus, IMChecklist
from src.api.db.models.im_checklist_item import (
    ChecklistItemStatus,
    IMChecklistItem,
)
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.checklist import (
    CategorySummary,
    ChecklistBatchUpdateRequest,
    ChecklistItemResponse,
    ChecklistItemUpdate,
    ChecklistResponse,
    ChecklistSummaryResponse,
    CreateFromVdrRequest,
    CreateFromVdrResponse,
)
from src.api.services.checklist_field_registry import get_all_fields, get_fields_for_style

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["checklist"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ITEM_STATUSES = {s.value for s in ChecklistItemStatus}


async def _get_document_with_checklist(
    document_id: uuid.UUID,
    session: AsyncSession,
    current_user: User,
) -> Document:
    """문서와 체크리스트(아이템 포함)를 함께 로드한다."""
    stmt = (
        select(Document)
        .options(
            selectinload(Document.checklist).selectinload(IMChecklist.items)
        )
        .where(Document.id == document_id)
    )
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    if doc.owner_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    return doc


# ---------------------------------------------------------------------------
# VDR 기반 IM 생성 시작
# ---------------------------------------------------------------------------


@router.post(
    "/documents/from-vdr",
    response_model=CreateFromVdrResponse,
    status_code=202,
    summary="VDR 기반 IM 생성 시작",
)
async def create_from_vdr(
    data: CreateFromVdrRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> CreateFromVdrResponse:
    """VDR 문서를 기반으로 IM 생성 워크플로우를 시작한다.

    1. Document 레코드 생성 (data_source=VDR)
    2. IMChecklist 레코드 생성 (status=EXTRACTING)
    3. 표준 필드 정의에서 IMChecklistItem 초기 레코드 생성 (status=MISSING)
    4. Celery 비동기 태스크로 VDR 문서 파싱 시작 (추후 Phase 4)
    """
    # 1. Document 생성
    doc = Document(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        company_name=data.company_name,
        project_name=data.project_name,
        data_source="VDR",
        im_style=data.im_style,
        status=DocumentStatus.COLLECTING.value,
        generation_config={"industry": data.industry},
    )
    session.add(doc)

    # 2. IMChecklist 생성
    checklist = IMChecklist(
        id=uuid.uuid4(),
        document_id=doc.id,
        transaction_id=data.transaction_id,
        vdr_document_ids=[str(vid) for vid in data.vdr_document_ids],
        status=ChecklistStatus.EXTRACTING.value,
    )
    session.add(checklist)

    # 3. 스타일별 필드로 초기 아이템 생성
    fields = get_fields_for_style(data.im_style)
    for i, field_def in enumerate(fields):
        item = IMChecklistItem(
            id=uuid.uuid4(),
            checklist_id=checklist.id,
            category=field_def.category,
            field_key=field_def.field_key,
            field_label=field_def.field_label,
            field_type=field_def.field_type,
            unit=field_def.unit,
            is_required=field_def.is_required,
            fiscal_year=field_def.fiscal_year,
            status=ChecklistItemStatus.MISSING.value,
            sort_order=i,
        )
        session.add(item)

    checklist.total_items = len(fields)
    checklist.missing_items = len(fields)

    await session.commit()
    await session.refresh(doc)
    await session.refresh(checklist)

    # 4. Celery 태스크로 VDR 파싱 시작
    extraction_task_id = None
    try:
        from src.api.tasks.vdr_extraction import extract_vdr_data_task
        result = extract_vdr_data_task.delay(str(doc.id), str(checklist.id))
        extraction_task_id = result.id
        checklist.extraction_task_id = extraction_task_id
        await session.commit()
    except Exception:
        logger.warning("Celery 태스크 큐 연결 실패 — 수동 파싱 필요")

    return CreateFromVdrResponse(
        document_id=doc.id,
        checklist_id=checklist.id,
        status=checklist.status,
        extraction_task_id=extraction_task_id,
    )


# ---------------------------------------------------------------------------
# 체크리스트 조회
# ---------------------------------------------------------------------------


@router.get(
    "/documents/{document_id}/checklist",
    response_model=ChecklistResponse,
    summary="체크리스트 전체 조회",
)
async def get_checklist(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> ChecklistResponse:
    """문서의 체크리스트와 전체 아이템을 반환한다."""
    doc = await _get_document_with_checklist(document_id, session, current_user)
    if doc.checklist is None:
        raise HTTPException(
            status_code=404, detail="이 문서에 체크리스트가 없습니다.",
        )
    return ChecklistResponse.model_validate(doc.checklist)


@router.get(
    "/documents/{document_id}/checklist/summary",
    response_model=ChecklistSummaryResponse,
    summary="카테고리별 완료율 요약",
)
async def get_checklist_summary(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> ChecklistSummaryResponse:
    """체크리스트의 카테고리별 완료 상황을 반환한다."""
    doc = await _get_document_with_checklist(document_id, session, current_user)
    checklist = doc.checklist
    if checklist is None:
        raise HTTPException(
            status_code=404, detail="이 문서에 체크리스트가 없습니다.",
        )

    # 카테고리별 집계
    cat_map: dict[str, dict[str, int]] = {}
    for item in checklist.items:
        cat = item.category
        if cat not in cat_map:
            cat_map[cat] = {"total": 0, "confirmed": 0, "missing": 0}
        cat_map[cat]["total"] += 1
        if item.status in ("CONFIRMED", "MODIFIED"):
            cat_map[cat]["confirmed"] += 1
        if item.status == "MISSING":
            cat_map[cat]["missing"] += 1

    categories = [
        CategorySummary(
            category=cat,
            total=counts["total"],
            confirmed=counts["confirmed"],
            missing=counts["missing"],
            completion_pct=(
                round(counts["confirmed"] / counts["total"] * 100, 1)
                if counts["total"] > 0 else 0.0
            ),
        )
        for cat, counts in sorted(cat_map.items())
    ]

    total = checklist.total_items or len(checklist.items)
    confirmed = sum(c.confirmed for c in categories)
    missing = sum(c.missing for c in categories)

    return ChecklistSummaryResponse(
        status=checklist.status,
        total_items=total,
        confirmed_items=confirmed,
        missing_items=missing,
        completion_pct=(
            round(confirmed / total * 100, 1) if total > 0 else 0.0
        ),
        categories=categories,
    )


# ---------------------------------------------------------------------------
# 아이템 수정
# ---------------------------------------------------------------------------


@router.patch(
    "/documents/{document_id}/checklist/items/{item_id}",
    response_model=ChecklistItemResponse,
    summary="개별 아이템 수정",
)
async def update_checklist_item(
    document_id: uuid.UUID,
    item_id: uuid.UUID,
    data: ChecklistItemUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> ChecklistItemResponse:
    """체크리스트 아이템의 값/상태/메모를 수정한다."""
    doc = await _get_document_with_checklist(document_id, session, current_user)
    checklist = doc.checklist
    if checklist is None:
        raise HTTPException(status_code=404, detail="체크리스트가 없습니다.")

    # 아이템 조회
    item = next((i for i in checklist.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")

    # 상태 검증
    if data.status is not None and data.status not in _VALID_ITEM_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 상태입니다. 허용: {_VALID_ITEM_STATUSES}",
        )

    # 수정 적용
    if data.confirmed_value is not None:
        item.confirmed_value = data.confirmed_value
        if item.status == ChecklistItemStatus.MISSING.value:
            item.status = ChecklistItemStatus.MODIFIED.value
        elif item.status == ChecklistItemStatus.EXTRACTED.value:
            if data.confirmed_value != item.extracted_value:
                item.status = ChecklistItemStatus.MODIFIED.value
            else:
                item.status = ChecklistItemStatus.CONFIRMED.value
    if data.status is not None:
        item.status = data.status
    if data.notes is not None:
        item.notes = data.notes

    # 집계 갱신
    checklist.update_counts()
    await session.commit()
    await session.refresh(item)

    return ChecklistItemResponse.model_validate(item)


@router.post(
    "/documents/{document_id}/checklist/items/batch-update",
    response_model=list[ChecklistItemResponse],
    summary="아이템 일괄 수정",
)
async def batch_update_items(
    document_id: uuid.UUID,
    data: ChecklistBatchUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[ChecklistItemResponse]:
    """여러 아이템을 한 번에 수정한다."""
    doc = await _get_document_with_checklist(document_id, session, current_user)
    checklist = doc.checklist
    if checklist is None:
        raise HTTPException(status_code=404, detail="체크리스트가 없습니다.")

    item_map = {i.id: i for i in checklist.items}
    updated: list[IMChecklistItem] = []

    for update in data.items:
        item = item_map.get(update.item_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"아이템 {update.item_id}을(를) 찾을 수 없습니다.",
            )
        if update.confirmed_value is not None:
            item.confirmed_value = update.confirmed_value
            if item.status == ChecklistItemStatus.MISSING.value:
                item.status = ChecklistItemStatus.MODIFIED.value
            elif item.status == ChecklistItemStatus.EXTRACTED.value:
                if update.confirmed_value != item.extracted_value:
                    item.status = ChecklistItemStatus.MODIFIED.value
                else:
                    item.status = ChecklistItemStatus.CONFIRMED.value
        if update.status is not None:
            if update.status not in _VALID_ITEM_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"유효하지 않은 상태: {update.status}",
                )
            item.status = update.status
        if update.notes is not None:
            item.notes = update.notes
        updated.append(item)

    checklist.update_counts()
    await session.commit()

    for item in updated:
        await session.refresh(item)

    return [ChecklistItemResponse.model_validate(i) for i in updated]


# ---------------------------------------------------------------------------
# 확정 + IM 생성 시작
# ---------------------------------------------------------------------------


@router.post(
    "/documents/{document_id}/checklist/confirm",
    response_model=ChecklistResponse,
    summary="체크리스트 확정 → IM 생성 시작",
)
async def confirm_checklist(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> ChecklistResponse:
    """체크리스트를 확정하고 IM 생성을 시작한다.

    필수 필드 중 MISSING 상태인 항목이 있으면 확정 불가.
    """
    doc = await _get_document_with_checklist(document_id, session, current_user)
    checklist = doc.checklist
    if checklist is None:
        raise HTTPException(status_code=404, detail="체크리스트가 없습니다.")

    if checklist.status not in (
        ChecklistStatus.REVIEW.value,
        ChecklistStatus.EXTRACTING.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({checklist.status})에서는 확정할 수 없습니다.",
        )

    # 필수 필드 검증
    missing_required = [
        item for item in checklist.items
        if item.is_required and item.status == ChecklistItemStatus.MISSING.value
    ]
    if missing_required:
        field_labels = [i.field_label for i in missing_required[:5]]
        raise HTTPException(
            status_code=400,
            detail=(
                f"필수 필드 {len(missing_required)}개가 누락되었습니다: "
                f"{', '.join(field_labels)}"
                + ("..." if len(missing_required) > 5 else "")
            ),
        )

    # 확정 처리
    checklist.status = ChecklistStatus.CONFIRMED.value
    checklist.confirmed_at = datetime.now(timezone.utc)
    checklist.update_counts()

    # Document 상태 업데이트
    doc.status = DocumentStatus.GENERATING.value

    await session.commit()

    # Celery 태스크로 IM 생성 시작
    try:
        from src.api.tasks.generate_im_from_checklist import (
            generate_im_from_checklist_task,
        )
        result = generate_im_from_checklist_task.delay(
            str(doc.id), str(checklist.id)
        )
        checklist.generation_task_id = result.id
        checklist.status = ChecklistStatus.GENERATING.value
        await session.commit()
    except Exception:
        logger.warning("Celery 태스크 큐 연결 실패")

    # Reload for response
    doc = await _get_document_with_checklist(document_id, session, current_user)
    return ChecklistResponse.model_validate(doc.checklist)


# ---------------------------------------------------------------------------
# 재파싱
# ---------------------------------------------------------------------------


@router.post(
    "/documents/{document_id}/checklist/reparse",
    response_model=ChecklistResponse,
    summary="VDR 문서 재파싱",
)
async def reparse_checklist(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> ChecklistResponse:
    """VDR 문서를 다시 파싱하여 체크리스트를 갱신한다.

    기존 사용자 수정 내역(CONFIRMED/MODIFIED)은 유지하고,
    EXTRACTED/MISSING 상태의 아이템만 재추출한다.
    """
    doc = await _get_document_with_checklist(document_id, session, current_user)
    checklist = doc.checklist
    if checklist is None:
        raise HTTPException(status_code=404, detail="체크리스트가 없습니다.")

    if checklist.status in (
        ChecklistStatus.GENERATING.value,
        ChecklistStatus.COMPLETED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({checklist.status})에서는 재파싱할 수 없습니다.",
        )

    # 상태 리셋
    checklist.status = ChecklistStatus.EXTRACTING.value
    await session.commit()

    # Celery 재파싱 태스크
    try:
        from src.api.tasks.vdr_extraction import extract_vdr_data_task
        result = extract_vdr_data_task.delay(str(doc.id), str(checklist.id))
        checklist.extraction_task_id = result.id
        await session.commit()
    except Exception:
        logger.warning("Celery 태스크 큐 연결 실패")

    doc = await _get_document_with_checklist(document_id, session, current_user)
    return ChecklistResponse.model_validate(doc.checklist)
