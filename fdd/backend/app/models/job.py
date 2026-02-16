"""Job 모델 — FDD-1801.

비동기 Job 오케스트레이션을 위한 상태 추적 모델.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.db_types import JsonbColumn


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, enum.Enum):
    REPORT_GENERATE = "REPORT_GENERATE"
    DATA_INGEST = "DATA_INGEST"
    ANOMALY_DETECT = "ANOMALY_DETECT"
    MASKING = "MASKING"
    PURGE = "PURGE"


class Job(Base):
    __tablename__ = "job"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), nullable=False, default=JobStatus.PENDING
    )

    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    input_params: Mapped[dict | None] = mapped_column(JsonbColumn, nullable=True)
    output_result: Mapped[dict | None] = mapped_column(JsonbColumn, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=600)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_job_status", "status"),
        Index("ix_job_deal", "deal_id"),
        Index("ix_job_type", "job_type"),
        Index("ix_job_created", "created_at"),
    )
