import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.db_types import JsonbColumn


class UploadType(str, enum.Enum):
    TB = "TB"
    GL = "GL"
    AR = "AR"
    AP = "AP"
    BANK = "BANK"
    DEBT = "DEBT"
    LEASE = "LEASE"


class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    DETECTING = "DETECTING"
    VALIDATING = "VALIDATING"
    INGESTING = "INGESTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ValidationSeverity(str, enum.Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class UploadFile(Base):
    __tablename__ = "upload_file"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Type detection
    detected_type: Mapped[UploadType | None] = mapped_column(
        Enum(UploadType), nullable=True
    )
    confirmed_type: Mapped[UploadType | None] = mapped_column(
        Enum(UploadType), nullable=True
    )
    detection_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )

    # Ingestion progress
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus), nullable=False, default=IngestionStatus.PENDING
    )
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Validation summary
    validation_summary: Mapped[dict | None] = mapped_column(JsonbColumn, nullable=True)

    # Metadata
    uploaded_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # VDR folder link
    vdr_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vdr_folder.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Entity link (multi-entity support)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    deal: Mapped["Deal"] = relationship()  # noqa: F821
    vdr_folder: Mapped["VdrFolder"] = relationship(  # noqa: F821
        back_populates="uploads"
    )
    validation_errors: Mapped[list["UploadValidationError"]] = relationship(
        back_populates="upload_file", cascade="all, delete-orphan"
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(  # noqa: F821
        back_populates="upload_file", cascade="all, delete-orphan"
    )


class UploadValidationError(Base):
    __tablename__ = "upload_validation_error"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_file.id", ondelete="CASCADE"),
        nullable=False,
    )
    severity: Mapped[ValidationSeverity] = mapped_column(
        Enum(ValidationSeverity), nullable=False
    )
    error_code: Mapped[str] = mapped_column(String(20), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    upload_file: Mapped["UploadFile"] = relationship(back_populates="validation_errors")
