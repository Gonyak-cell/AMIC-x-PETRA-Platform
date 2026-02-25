"""IM Audit Log 라우터 — 감사 로그 조회/내보내기."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.audit import AuditLog
from src.api.db.session import get_async_session
from src.api.schemas.audit import AuditLogListResponse, AuditLogRead

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit"])


async def _list_audit_logs(
    db: AsyncSession,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if start_date is not None:
        cutoff = datetime.combine(start_date, datetime.min.time())
        stmt = stmt.where(AuditLog.created_at >= cutoff)
        count_stmt = count_stmt.where(AuditLog.created_at >= cutoff)
    if end_date is not None:
        cutoff = datetime.combine(end_date, datetime.max.time())
        stmt = stmt.where(AuditLog.created_at <= cutoff)
        count_stmt = count_stmt.where(AuditLog.created_at <= cutoff)

    total = (await db.execute(count_stmt)).scalar_one() or 0
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


@router.get("", response_model=AuditLogListResponse)
async def search_audit_logs(
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_session),
) -> AuditLogListResponse:
    items, total = await _list_audit_logs(
        db,
        entity_type=entity_type,
        action=action,
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


@router.get("/export")
async def export_audit_logs(
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    items, _ = await _list_audit_logs(
        db, entity_type=entity_type, action=action,
        start_date=start_date, end_date=end_date, limit=10000, offset=0,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "User", "Action", "Entity Type", "Entity ID"])
    for item in items:
        writer.writerow([
            item.created_at.isoformat() if item.created_at else "",
            item.actor_email or "",
            item.action.value if hasattr(item.action, "value") else str(item.action),
            item.entity_type,
            str(item.entity_id),
        ])
    csv_bytes = output.getvalue().encode("utf-8-sig")
    filename = f"im_audit_log_{date.today().isoformat()}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
