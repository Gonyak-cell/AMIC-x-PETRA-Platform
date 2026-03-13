"""Document ORM 모델 (T-I04).

> 마지막 수정: 2026-03-13 16:16:00

IM 문서 생성 작업 상태 및 결과를 저장한다.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.db.base import Base

if TYPE_CHECKING:
    from src.api.db.models.diagram import Diagram
    from src.api.db.models.im_checklist import IMChecklist
    from src.api.db.models.im_ralph_session import IMRalphSession
    from src.api.db.models.user import User


class DocumentStatus(str, enum.Enum):
    """문서 생성 상태."""

    AWAITING_UPLOAD = "AWAITING_UPLOAD"
    PENDING = "PENDING"
    COLLECTING = "COLLECTING"
    ANALYZING = "ANALYZING"
    GENERATING = "GENERATING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    QUALITY_CONDITIONAL = "QUALITY_CONDITIONAL"
    QUALITY_FAILED = "QUALITY_FAILED"
    FAILED = "FAILED"


class Document(Base):
    """IM 문서 모델."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    corp_code: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    project_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    data_source: Mapped[str] = mapped_column(
        String(20),
        default="DART",
    )

    # 생성 설정
    im_style: Mapped[str] = mapped_column(
        String(20),
        default="FULL",
    )
    sections: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    generation_config: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )

    # 상태 추적
    status: Mapped[str] = mapped_column(
        String(20),
        default=DocumentStatus.PENDING.value,
        index=True,
    )
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stage_details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )

    # 출력 파일
    pptx_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    pdf_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # 품질 게이트 결과
    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    quality_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    quality_issues: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    slide_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    generation_profile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    supported_formats: Mapped[list[str] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
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
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    owner: Mapped[User] = relationship(
        back_populates="documents",
    )
    checklist: Mapped[IMChecklist | None] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ralph_sessions: Mapped[list[IMRalphSession]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    diagrams: Mapped[list[Diagram]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    @property
    def industry(self) -> str | None:
        """generation_config에서 industry를 반환한다."""
        config = self.generation_config or {}
        return config.get("industry")

    __table_args__ = (
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_created_at", "created_at"),
        Index(
            "uq_documents_corp_code_active",
            "corp_code",
            unique=True,
            postgresql_where=text(
                "corp_code IS NOT NULL AND "
                "status IN ('PENDING', 'COLLECTING', 'ANALYZING', "
                "'GENERATING', 'RENDERING')"
            ),
        ),
    )
