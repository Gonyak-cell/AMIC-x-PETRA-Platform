"""Manual routing override decisions for VDR documents."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VdrDocumentRoutingOverride(Base, TimestampMixin):
    """Human-reviewed workstream override for a single VDR document."""

    __tablename__ = "vdr_document_routing_overrides"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vdr_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("vdr_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    primary_workstream: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    workstream_tags: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    override_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
