"""Normalized parsed document chunks for cross-workstream traceability."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DocumentChunk(Base, TimestampMixin):
    """Normalized chunk rows derived from parsed VDR documents."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("vdr_document_id", "chunk_id", name="uq_document_chunks_document_chunk"),
    )

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
        index=True,
    )
    vdr_text_cache_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("vdr_text_caches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(String(120), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locator_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_text: Mapped[str | None] = mapped_column(Text, nullable=True)
