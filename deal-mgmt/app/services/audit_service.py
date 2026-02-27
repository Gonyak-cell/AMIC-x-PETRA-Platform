"""감사 로그 기록 + 조회 서비스."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import AuditAction


def _json_safe(val: Any) -> Any:
    """SQLAlchemy 모델 속성값을 JSON 직렬화 가능 타입으로 변환한다."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, enum.Enum):
        return val.value
    if isinstance(val, dict):
        return {k: _json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_json_safe(item) for item in val]
    return val


def _sanitize_for_json(data: dict | None) -> dict | None:
    """감사 로그 JSONB 저장 전 비-직렬화 타입을 변환한다."""
    if data is None:
        return None
    return {k: _json_safe(v) for k, v in data.items()}


async def list_audit_logs(
    db: AsyncSession,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """감사 로그를 필터/검색하고 총 개수를 반환한다."""
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


async def record(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    actor_email: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    notes: str | None = None,
) -> None:
    """감사 로그 1건을 DB에 기록한다 (커밋은 호출 측에서)."""
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_email=actor_email,
        old_value=_sanitize_for_json(old_value),
        new_value=_sanitize_for_json(new_value),
        notes=notes,
    )
    db.add(log)
