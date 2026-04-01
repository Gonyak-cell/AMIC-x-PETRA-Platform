"""NDA 마크업 버전 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NdaMarkupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nda_id: uuid.UUID
    attachment_id: uuid.UUID | None = None
    version_label: str
    version_number: int
    version_date: str
    source_party: str | None = None
    markup_type: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    changes_summary: str | None = None
    key_changes: list[Any] | None = None
    redline_issues_count: int | None = None
    base_version_id: uuid.UUID | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime

    has_file: bool = False
    has_redline: bool = False

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> NdaMarkupOut:  # type: ignore[override]
        instance = super().model_validate(obj, **kwargs)
        if hasattr(obj, "file_path"):
            instance.has_file = bool(obj.file_path)
        if hasattr(obj, "redline_file_path"):
            instance.has_redline = bool(obj.redline_file_path)
        return instance


class NdaMarkupListResponse(BaseModel):
    items: list[NdaMarkupOut]
    total: int
    limit: int
    offset: int
