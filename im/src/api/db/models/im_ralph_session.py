"""IM Ralph Loop 세션 모델 — 반복 이력, 점수 추이, 비용 추적."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.db.base import Base


class IMRalphSession(Base):
    """IM Ralph Loop 실행 세션.

    각 문서 생성 요청마다 하나의 세션이 생성되며,
    반복 이력, 차원별 점수, 비용 등을 추적한다.

    - pass_number=1: Draft (초기 생성 직후)
    - pass_number=2: Final (체크리스트 확인 후)
    """

    __tablename__ = "im_ralph_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Pass 번호: 1=Draft, 2=Final
    pass_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
    )

    # 문서 유형 (im_full, im_teaser 등)
    doc_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )

    # 상태: PLANNING / GENERATING / VALIDATING / COMPLETED / FAILED / BUDGET_EXCEEDED
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PLANNING",
    )

    # 반복 상태 (JSONB)
    prd: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 결과 집계
    total_iterations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    final_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    section_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 출력
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 에러/플래그
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    critical_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 학습 패턴
    learned_patterns: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 요청자
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    document = relationship("Document", back_populates="ralph_sessions")

    __table_args__ = (
        Index("ix_im_ralph_document", "document_id"),
        Index("ix_im_ralph_status", "status"),
        Index("ix_im_ralph_doc_pass", "document_id", "pass_number"),
    )
