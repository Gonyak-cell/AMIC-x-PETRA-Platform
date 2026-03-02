"""M&A Audit Log 라우터 — 감사 로그 조회/내보내기."""

from __future__ import annotations

import csv
import io
import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, require_role
from app.schemas.audit import AuditLogListResponse, AuditLogRead
from app.services.audit_service import list_audit_logs

router = APIRouter(tags=["Audit"])


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def search_audit_logs(
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_role("ADMIN", "MANAGER")),
) -> AuditLogListResponse:
    """감사 로그를 검색/필터한다."""
    items, total = await list_audit_logs(
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


@router.get("/audit-logs/export")
async def export_audit_logs(
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_role("ADMIN", "MANAGER")),
) -> StreamingResponse:
    """감사 로그를 CSV 파일로 내보낸다 (배치 스트리밍)."""
    _batch_size = 1000

    async def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Timestamp", "User", "Action", "Entity Type", "Entity ID", "Old Value", "New Value", "Notes"])
        yield buf.getvalue().encode("utf-8-sig")

        offset = 0
        while True:
            items, _ = await list_audit_logs(
                db,
                entity_type=entity_type,
                action=action,
                start_date=start_date,
                end_date=end_date,
                limit=_batch_size,
                offset=offset,
            )
            if not items:
                break
            buf = io.StringIO()
            writer = csv.writer(buf)
            for item in items:
                writer.writerow(
                    [
                        item.created_at.isoformat() if item.created_at else "",
                        item.actor_email or "",
                        item.action.value,
                        item.entity_type,
                        str(item.entity_id),
                        json.dumps(item.old_value, ensure_ascii=False) if item.old_value else "",
                        json.dumps(item.new_value, ensure_ascii=False) if item.new_value else "",
                        item.notes or "",
                    ]
                )
            yield buf.getvalue().encode("utf-8")
            if len(items) < _batch_size:
                break
            offset += _batch_size

    filename = f"ma_audit_log_{date.today().isoformat()}.csv"
    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
