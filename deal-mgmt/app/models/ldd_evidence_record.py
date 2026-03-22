"""Normalized evidence traceability records for LDD reports."""

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LDDEvidenceRecord(Base, TimestampMixin):
    """Current evidence snapshot used to compile an LDD item."""

    __tablename__ = "ldd_evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ldd_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ldd_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    item_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    section_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    vdr_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("vdr_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reference_label: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_workstream: Mapped[str | None] = mapped_column(String(30), nullable=True)
    workstream_tags: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    evidence_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    directness: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_page: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_locator: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_foreign_workstream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_unresolved_reference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_in_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_in_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    analysis_phase: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
