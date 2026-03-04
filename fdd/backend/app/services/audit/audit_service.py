"""Audit Log 서비스 — FDD-1702.

감사 로그 검색/필터 + 변경 전/후 추적.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    user_id: uuid.UUID | None = None,
    deal_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """감사 로그를 필터/검색하고 총 개수를 함께 반환한다."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
        count_stmt = count_stmt.where(AuditLog.entity_id == entity_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if deal_id is not None:
        stmt = stmt.where(AuditLog.deal_id == deal_id)
        count_stmt = count_stmt.where(AuditLog.deal_id == deal_id)
    if start_date is not None:
        stmt = stmt.where(
            AuditLog.created_at >= datetime.combine(start_date, datetime.min.time())
        )
        count_stmt = count_stmt.where(
            AuditLog.created_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        stmt = stmt.where(
            AuditLog.created_at <= datetime.combine(end_date, datetime.max.time())
        )
        count_stmt = count_stmt.where(
            AuditLog.created_at <= datetime.combine(end_date, datetime.max.time())
        )

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    items = list(db.scalars(stmt).all())

    return items, total


def create_enhanced_audit_log(
    db: Session,
    *,
    deal_id: uuid.UUID | None = None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    actor: str = "system",
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
    user_role: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    changed_fields: list[str] | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    expires_at: datetime | None = None,
) -> AuditLog:
    """확장된 감사 로그를 생성한다 (변경 전/후 상태 포함)."""
    log = AuditLog(
        deal_id=deal_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        ip_address=ip_address,
        user_agent=user_agent,
        old_value=old_value,
        new_value=new_value,
        before_state=before_state,
        after_state=after_state,
        changed_fields=changed_fields,
        session_id=session_id,
        request_id=request_id,
        expires_at=expires_at,
    )
    db.add(log)
    db.flush()
    return log


def get_entity_audit_trail(
    db: Session,
    entity_type: str,
    entity_id: uuid.UUID,
) -> list[AuditLog]:
    """특정 엔티티의 전체 변경 이력을 시간순으로 반환한다."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def compute_changed_fields(before: dict | None, after: dict | None) -> list[str]:
    """before/after 딕셔너리를 비교하여 변경된 필드 목록을 반환한다."""
    if before is None and after is None:
        return []
    if before is None:
        return list(after.keys()) if after else []
    if after is None:
        return list(before.keys())

    changed = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed
