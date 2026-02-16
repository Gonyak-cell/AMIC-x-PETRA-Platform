"""Export record Pydantic schemas — Phase 5."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.export_record import ExportFormat, ExportModule, ExportStatus


class ExportRecordRead(BaseModel):
    id: uuid.UUID
    module: ExportModule
    type: str
    name: str
    format: ExportFormat
    file_size_bytes: int | None
    status: ExportStatus
    download_url: str | None
    expires_at: datetime | None
    created_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class PaginatedExports(BaseModel):
    items: list[ExportRecordRead]
    total: int
    page: int
    size: int


class BatchDownloadRequest(BaseModel):
    export_ids: list[uuid.UUID]
