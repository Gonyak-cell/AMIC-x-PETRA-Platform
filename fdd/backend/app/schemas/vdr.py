"""VDR (Virtual Data Room) Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.vdr import VdrFolderType


class VdrFolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    folder_type: VdrFolderType
    parent_id: uuid.UUID | None = None
    is_required: bool = False


class VdrFolderCreate(VdrFolderBase):
    pass


class VdrFolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    order_index: int | None = None


class VdrFolderRead(VdrFolderBase):
    id: uuid.UUID
    deal_id: uuid.UUID
    order_index: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VdrFolderTree(VdrFolderRead):
    """Folder with nested children for tree view."""

    children: list["VdrFolderTree"] = []
    file_count: int = 0


class VdrInitRequest(BaseModel):
    """Request to initialize default VDR folder structure."""

    include_custom: bool = False
