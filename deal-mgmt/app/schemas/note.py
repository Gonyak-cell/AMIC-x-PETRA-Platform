from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NoteType


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    author_email: str
    content: str
    note_type: NoteType
    parent_id: uuid.UUID | None = None
    is_pinned: bool
    mentions: list[str] | None = None
    attachments: list[dict] | None = None
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    note_type: NoteType = NoteType.COMMENT
    parent_id: uuid.UUID | None = None
    is_pinned: bool = False
    mentions: list[str] | None = None
    attachments: list[dict] | None = None


class NoteUpdate(BaseModel):
    content: str | None = Field(None, min_length=1, max_length=10000)
    note_type: NoteType | None = None
    is_pinned: bool | None = None
    mentions: list[str] | None = None
    attachments: list[dict] | None = None


class NoteListResponse(BaseModel):
    items: list[NoteOut]
    total: int
