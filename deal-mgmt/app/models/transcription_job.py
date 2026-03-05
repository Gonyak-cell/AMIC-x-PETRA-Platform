"""녹음 변환 작업 — Clova STT + LLM 자동 회의록 생성."""

import uuid

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import MeetingPhase, TranscriptionJobStatus


class TranscriptionJob(Base, TimestampMixin):
    """녹음 파일 → STT → LLM 구조화 → 회의록 자동 생성 작업."""

    __tablename__ = "transcription_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 입력 메타데이터
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    meeting_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    meeting_phase: Mapped[MeetingPhase] = mapped_column(Enum(MeetingPhase), nullable=False)
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("buyer_candidates.id"),
        nullable=True,
    )

    # 참석자 (사용자 입력, JSON 배열)
    attendees_json: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # 오디오 파일
    audio_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    audio_file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 처리 상태
    status: Mapped[TranscriptionJobStatus] = mapped_column(
        Enum(TranscriptionJobStatus),
        nullable=False,
        default=TranscriptionJobStatus.PENDING,
    )

    # STT 결과
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LLM 구조화 결과
    minutes_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # 확정된 미팅 로그 (approve 후)
    meeting_log_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("meeting_logs.id"),
        nullable=True,
    )

    # 비용 추적
    stt_cost_krw: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    llm_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 에러
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 생성자
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
