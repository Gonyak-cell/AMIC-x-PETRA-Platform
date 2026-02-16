"""Audit Log API — FDD-1702.

감사 로그 검색/필터 + 엔티티별 이력 조회.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.audit import AuditAction
from app.schemas.audit import AuditLogListResponse, AuditLogRead
from app.services.audit.audit_service import get_entity_audit_trail, list_audit_logs

router = APIRouter(tags=["audit"])


@router.get("/audit-logs", response_model=AuditLogListResponse)
def search_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    deal_id: uuid.UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = require_permission(Permission.AUDIT_VIEW),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    """감사 로그를 검색/필터한다."""
    items, total = list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        deal_id=deal_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        total=total,
        items=[AuditLogRead.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
    )


@router.get("/audit-logs/export")
def export_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    deal_id: uuid.UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: CurrentUser = require_permission(Permission.AUDIT_VIEW),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """감사 로그를 CSV 파일로 내보낸다."""
    items, _ = list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        deal_id=deal_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp",
        "User",
        "Action",
        "Entity Type",
        "Entity ID",
        "Deal ID",
        "IP Address",
        "Changed Fields",
    ])
    for item in items:
        writer.writerow([
            item.created_at.isoformat() if item.created_at else "",
            item.user_email or item.actor,
            item.action.value if hasattr(item.action, "value") else str(item.action),
            item.entity_type,
            str(item.entity_id),
            str(item.deal_id) if item.deal_id else "",
            item.ip_address or "",
            ", ".join(item.changed_fields) if item.changed_fields else "",
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    filename = f"audit_log_export_{date.today().isoformat()}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/audit-logs/entity/{entity_type}/{entity_id}",
    response_model=list[AuditLogRead],
)
def get_audit_trail(
    entity_type: str,
    entity_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.AUDIT_VIEW),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    """특정 엔티티의 전체 변경 이력을 조회한다."""
    items = get_entity_audit_trail(db, entity_type, entity_id)
    return [AuditLogRead.model_validate(item) for item in items]
