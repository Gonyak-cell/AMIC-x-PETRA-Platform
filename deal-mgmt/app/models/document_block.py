"""문서 블록 — Phase 2 조항/행 단위 텍스트 비교용 스텁 모델."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import DocumentBlockType


class DocumentBlock(Base):
    """문서 블록 — 리비전 내 조항/행 단위 텍스트 블록 (Phase 2 구현 예정)."""

    __tablename__ = "document_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    block_key: Mapped[str] = mapped_column(String(100), nullable=False)
    block_type: Mapped[DocumentBlockType] = mapped_column(Enum(DocumentBlockType), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
