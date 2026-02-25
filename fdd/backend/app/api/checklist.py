"""Checklist API — FDD 체크리스트 조회/리뷰/수정/Finalize."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.schemas.fdd_checklist import (
    ChecklistBulkUpdate,
    ChecklistFinalizeRequest,
    ChecklistItemRead,
    ChecklistItemUpdate,
    ChecklistRead,
    VdrLinkRead,
)
from app.services.checklist_service import ChecklistService

router = APIRouter(prefix="/deals/{deal_id}/checklist", tags=["checklist"])


def _checklist_to_response(checklist, service: ChecklistService) -> dict:
    """FddChecklist ORM → ChecklistRead 직렬화 헬퍼."""
    summary = service.get_checklist_summary(checklist)
    items = []
    for item in checklist.items:
        vdr_links = [
            VdrLinkRead(
                id=link.id,
                upload_file_id=link.upload_file_id,
                vdr_folder_id=link.vdr_folder_id,
                evidence_link_id=link.evidence_link_id,
                source_detail=link.source_detail,
                description=link.description,
            )
            for link in (item.vdr_links or [])
        ]
        items.append(
            ChecklistItemRead(
                id=item.id,
                category=item.category,
                order_index=item.order_index,
                title=item.title,
                description=item.description,
                auto_finding=item.auto_finding,
                auto_amount=str(item.auto_amount) if item.auto_amount else None,
                user_correction=item.user_correction,
                user_amount=str(item.user_amount) if item.user_amount else None,
                status=item.status,
                severity=item.severity,
                reviewed_by=item.reviewed_by,
                reviewed_at=item.reviewed_at,
                vdr_links=vdr_links,
                metadata=item.extra_metadata,
            )
        )

    return ChecklistRead(
        id=checklist.id,
        deal_id=checklist.deal_id,
        version=checklist.version,
        status=checklist.status,
        items=items,
        notes=checklist.notes,
        created_by=checklist.created_by,
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
        finalized_at=checklist.finalized_at,
        **summary,
    )


@router.get("", response_model=ChecklistRead)
def get_checklist(
    deal_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """최신 FDD 체크리스트 조회 (항목 + VDR 링크 포함).

    Args:
        deal_id: Deal UUID

    Returns:
        ChecklistRead (항목 + 요약 통계)
    """
    service = ChecklistService(db)
    checklist = service.get_latest_checklist(deal_id)
    return _checklist_to_response(checklist, service)


@router.get("/{checklist_id}", response_model=ChecklistRead)
def get_checklist_by_id(
    deal_id: UUID,
    checklist_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """특정 버전 체크리스트 조회.

    Args:
        deal_id: Deal UUID
        checklist_id: FddChecklist UUID

    Returns:
        ChecklistRead
    """
    service = ChecklistService(db)
    checklist = service.get_checklist_by_id(checklist_id, deal_id)
    return _checklist_to_response(checklist, service)


@router.put("/items/{item_id}", response_model=ChecklistItemRead)
def update_checklist_item(
    deal_id: UUID,
    item_id: UUID,
    body: ChecklistItemUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """체크리스트 항목 리뷰/수정.

    Args:
        deal_id: Deal UUID
        item_id: FddChecklistItem UUID
        body: 상태 + 사용자 수정 내용

    Returns:
        업데이트된 ChecklistItemRead
    """
    from app.models.fdd_checklist import FddChecklistItem

    # deal_id 소속 검증 (IDOR 방지)
    raw_item = db.get(FddChecklistItem, item_id)
    if raw_item is None or raw_item.checklist.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    service = ChecklistService(db)
    item = service.update_item(item_id, body, current_user.email)
    db.commit()
    db.refresh(item)

    return ChecklistItemRead(
        id=item.id,
        category=item.category,
        order_index=item.order_index,
        title=item.title,
        description=item.description,
        auto_finding=item.auto_finding,
        auto_amount=str(item.auto_amount) if item.auto_amount else None,
        user_correction=item.user_correction,
        user_amount=str(item.user_amount) if item.user_amount else None,
        status=item.status,
        severity=item.severity,
        reviewed_by=item.reviewed_by,
        reviewed_at=item.reviewed_at,
        vdr_links=[],
        metadata=item.extra_metadata,
    )


@router.put("/{checklist_id}/bulk-update", response_model=list[ChecklistItemRead])
def bulk_update_items(
    deal_id: UUID,
    checklist_id: UUID,
    body: ChecklistBulkUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """체크리스트 항목 일괄 업데이트.

    Args:
        deal_id: Deal UUID
        checklist_id: FddChecklist UUID
        body: 항목 업데이트 목록

    Returns:
        업데이트된 항목 목록
    """
    service = ChecklistService(db)
    items = service.bulk_update_items(checklist_id, body.items, current_user.email)
    db.commit()

    result = []
    for item in items:
        db.refresh(item)
        result.append(
            ChecklistItemRead(
                id=item.id,
                category=item.category,
                order_index=item.order_index,
                title=item.title,
                description=item.description,
                auto_finding=item.auto_finding,
                auto_amount=str(item.auto_amount) if item.auto_amount else None,
                user_correction=item.user_correction,
                user_amount=str(item.user_amount) if item.user_amount else None,
                status=item.status,
                severity=item.severity,
                reviewed_by=item.reviewed_by,
                reviewed_at=item.reviewed_at,
                vdr_links=[],
                metadata=item.extra_metadata,
            )
        )
    return result


@router.post("/{checklist_id}/finalize", response_model=ChecklistRead)
def finalize_checklist(
    deal_id: UUID,
    checklist_id: UUID,
    body: ChecklistFinalizeRequest,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """체크리스트 확정 (Finalize).

    Finalize 후 체크리스트 수정사항이 반영된 보고서를 생성할 수 있다.

    Args:
        deal_id: Deal UUID
        checklist_id: FddChecklist UUID
        body: 확정 메모

    Returns:
        확정된 ChecklistRead
    """
    service = ChecklistService(db)
    try:
        checklist = service.finalize_checklist(
            checklist_id, deal_id, current_user.email, body.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _checklist_to_response(checklist, service)


@router.get("/items/{item_id}/vdr-links", response_model=list[VdrLinkRead])
def get_item_vdr_links(
    deal_id: UUID,
    item_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """체크리스트 항목의 VDR 소스 목록 조회.

    Args:
        deal_id: Deal UUID
        item_id: FddChecklistItem UUID

    Returns:
        VdrLinkRead 목록
    """
    from app.models.fdd_checklist import FddChecklistItem

    item = db.get(FddChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    # deal_id 소속 검증 (IDOR 방지)
    if item.checklist.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    return [
        VdrLinkRead(
            id=link.id,
            upload_file_id=link.upload_file_id,
            vdr_folder_id=link.vdr_folder_id,
            evidence_link_id=link.evidence_link_id,
            source_detail=link.source_detail,
            description=link.description,
        )
        for link in (item.vdr_links or [])
    ]
