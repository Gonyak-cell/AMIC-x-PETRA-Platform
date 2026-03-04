"""Template Model - 템플릿 저장 모델.

EPIC-10: 고객 PPT/Word 템플릿 관리를 위한 DB 모델.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.db_types import JsonbColumn


class TemplateStatus(str, enum.Enum):
    """템플릿 상태."""

    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    ARCHIVED = "archived"


class TemplateType(str, enum.Enum):
    """템플릿 타입."""

    PPTX = "pptx"
    DOCX = "docx"


class Template(Base):
    """템플릿 모델.

    고객 PPT/Word 템플릿 정보를 저장합니다.
    실제 파일은 file_path에 저장되고, 메타데이터는 contract에 저장됩니다.
    """

    __tablename__ = "template"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[TemplateType] = mapped_column(
        Enum(TemplateType), nullable=False, default=TemplateType.PPTX
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract: Mapped[dict] = mapped_column(JsonbColumn, nullable=False)
    status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus), nullable=False, default=TemplateStatus.DRAFT
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
