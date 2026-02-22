"""감사 로그 기록 서비스."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import AuditAction


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
        old_value=old_value,
        new_value=new_value,
        notes=notes,
    )
    db.add(log)
