"""Ralph Loop 세션 모델 — 반복 이력, 점수 추이, 비용 추적."""

import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RalphSessionStatus(str):
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class RalphSession(Base, TimestampMixin):
    """Ralph Loop 실행 세션.

    각 문서 생성 요청마다 하나의 세션이 생성되며,
    반복 이력, 차원별 점수, 비용 등을 추적한다.
    """

    __tablename__ = "ralph_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 문서 유형 및 설정
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)  # ldd_full, tm, dm, im
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=RalphSessionStatus.PLANNING)

    # 반복 상태 (JSONB)
    prd: Mapped[dict | None] = mapped_column(JSONB, nullable=True)           # PRD 수용 기준
    progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)      # ProgressTracker 직렬화
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)        # LoopConfig

    # 결과 집계
    total_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    section_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 출력 파일
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    output_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 최종 산출물 (JSON 문자열 — assemble_document 결과)
    final_artifact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 학습 패턴 (Phase 2: AGENTS.md DB 기반)
    learned_patterns: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 에러/플래그
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    critical_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 요청자
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
