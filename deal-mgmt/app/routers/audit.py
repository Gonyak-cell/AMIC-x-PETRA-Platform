"""M&A Audit Log 라우터 — 감사 로그 조회/내보내기."""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
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
    claims: JWTClaims = Depends(get_jwt_claims),
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
    claims: JWTClaims = Depends(get_jwt_claims),
) -> StreamingResponse:
    """감사 로그를 CSV 파일로 내보낸다."""
    items, _ = await list_audit_logs(
        db,
        entity_type=entity_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0,
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
    filename = f"ma_audit_log_{date.today().isoformat()}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
