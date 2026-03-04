"""Diagram ORM 모델.

Excalidraw 다이어그램 데이터를 저장한다.
주주관계도, 조직도, 거래구조도, 가치사슬도 등.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.db.base import Base

if TYPE_CHECKING:
    from src.api.db.models.document import Document


class Diagram(Base):
    """Excalidraw 다이어그램 모델."""

    __tablename__ = "diagrams"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    diagram_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # Excalidraw JSON 데이터 (elements + appState + files)
    excalidraw_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
    )

    # 내보내기된 PNG 경로 (PPTX 파이프라인용)
    png_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    document: Mapped[Document] = relationship(
        back_populates="diagrams",
    )

    __table_args__ = (
        Index("ix_diagrams_document_type", "document_id", "diagram_type"),
    )
