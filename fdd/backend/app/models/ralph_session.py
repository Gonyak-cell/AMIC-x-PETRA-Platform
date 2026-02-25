"""FDD Ralph Loop 세션 모델."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.utils.db_types import JsonbColumn


class FddRalphSessionStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class FddRalphSession(Base):
    """FDD Ralph Loop 세션.

    각 Ralph Loop 실행(Draft Pass / Final Pass)에 대한 기록.
    progress JsonbColumn에 섹션별 반복 상세가 저장된다.
    """

    __tablename__ = "fdd_ralph_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deal.id"), nullable=False, index=True)
    pass_type = Column(String(10), nullable=False)  # "draft" | "final"
    status = Column(String(20), nullable=False, default=FddRalphSessionStatus.PENDING)

    # 연관 ID (선택)
    checklist_id = Column(UUID(as_uuid=True), nullable=True)
    report_version_id = Column(UUID(as_uuid=True), nullable=True)

    # PRD & 설정
    prd = Column(JsonbColumn, nullable=True)
    config = Column(JsonbColumn, nullable=True)

    # 진행 & 결과
    progress = Column(JsonbColumn, nullable=True)
    total_iterations = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    section_scores = Column(JsonbColumn, nullable=True)

    # 출력
    refined_ir = Column(JsonbColumn, nullable=True)  # Refined Report IR JSON

    # 에러 & 플래그
    error_message = Column(Text, nullable=True)
    critical_flags = Column(JsonbColumn, nullable=True)

    # 학습 패턴
    learned_patterns = Column(JsonbColumn, nullable=True)

    # 메타
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
