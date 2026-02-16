"""Audit Log Pydantic 스키마 — FDD-1702."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.audit import AuditAction


class AuditLogRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID
    action: AuditAction
    actor: str
    old_value: dict | None
    new_value: dict | None
    user_id: uuid.UUID | None
    user_email: str | None
    user_role: str | None
    ip_address: str | None
    before_state: dict | None
    after_state: dict | None
    changed_fields: list[str] | None
    session_id: str | None
    request_id: str | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogRead]
    limit: int
    offset: int
