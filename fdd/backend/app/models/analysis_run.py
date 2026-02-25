"""AnalysisRun 모델 — VDR 기반 자동 분석 실행 추적.

VDR에 업로드된 파일을 기반으로 QoE/NWC/Debt 엔진을 실행하고
FDD 체크리스트를 자동 생성하는 분석 실행 단위.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.db_types import JsonbColumn


class AnalysisRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisRun(Base):
    """VDR 기반 자동 분석 실행 추적.

    하나의 AnalysisRun은 하나의 FddChecklist를 생성한다.
    """

    __tablename__ = "analysis_run"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual",
        comment="분석 트리거: manual, vdr_upload, scheduled",
    )
    status: Mapped[AnalysisRunStatus] = mapped_column(
        Enum(AnalysisRunStatus), nullable=False, default=AnalysisRunStatus.PENDING
    )

    # 입력/출력
    input_file_ids: Mapped[dict | None] = mapped_column(
        JsonbColumn, nullable=True, comment="분석에 사용된 upload_file_id 목록"
    )
    output_checklist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fdd_checklist.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 진행률
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 교차검증 / QA 결과
    cross_verify_summary: Mapped[dict | None] = mapped_column(
        JsonbColumn, nullable=True, comment="교차검증 결과 요약 JSON"
    )
    qa_result: Mapped[dict | None] = mapped_column(
        JsonbColumn, nullable=True, comment="레포트 QA 결과 JSON"
    )

    # 타임스탬프
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_analysis_run_deal", "deal_id"),
        Index("ix_analysis_run_status", "status"),
    )
