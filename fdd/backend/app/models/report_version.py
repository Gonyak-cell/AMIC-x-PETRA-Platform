import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.db_types import JsonbColumn


class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"


class ReportVersion(Base):
    __tablename__ = "report_version"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), nullable=False, default=ReportStatus.DRAFT
    )

    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False, default="pptx")

    options: Mapped[dict] = mapped_column(JsonbColumn, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    deal: Mapped["Deal"] = relationship(  # noqa: F821
        back_populates="report_versions"
    )
