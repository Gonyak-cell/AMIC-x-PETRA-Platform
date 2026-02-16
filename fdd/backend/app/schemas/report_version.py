"""Report Version Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.report_version import ReportStatus


class ReportVersionCreate(BaseModel):
    file_format: str = Field(default="pptx", pattern=r"^(pptx|docx)$")
    include_qoe: bool = True
    include_nwc: bool = True
    include_debt: bool = True
    include_issues: bool = True
    notes: str | None = None


class ReportVersionRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    version: int
    status: ReportStatus
    file_path: str | None
    file_format: str
    options: dict
    notes: str | None
    created_by: str
    created_at: datetime
    finalized_at: datetime | None

    model_config = {"from_attributes": True}


class ReportVersionFinalize(BaseModel):
    notes: str | None = None
