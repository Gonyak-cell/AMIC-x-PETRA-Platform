"""Export record model — Phase 5 Portal endpoints."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExportModule(str, enum.Enum):
    FDD = "fdd"
    KIIS = "kiis"
    IM = "im"


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    ZIP = "zip"


class ExportRecord(Base):
    __tablename__ = "export_record"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    module: Mapped[ExportModule] = mapped_column(Enum(ExportModule), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[ExportFormat] = mapped_column(Enum(ExportFormat), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[ExportStatus] = mapped_column(
        Enum(ExportStatus), nullable=False, default=ExportStatus.PENDING
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    download_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_export_record_user", "created_by_user_id"),
        Index("ix_export_record_module", "module"),
        Index("ix_export_record_status", "status"),
        Index("ix_export_record_created", "created_at"),
    )
