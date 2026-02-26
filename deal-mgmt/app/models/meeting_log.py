"""미팅 로그 — 마케팅/협상 단계 공용."""

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ConditionMatchLevel, MeetingChannel, MeetingPhase, MeetingStatus


class MeetingLog(Base, TimestampMixin):
    """마케팅/협상 미팅 로그."""

    __tablename__ = "meeting_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 단계 구분
    meeting_phase: Mapped[MeetingPhase] = mapped_column(Enum(MeetingPhase), nullable=False)

    # 기본 정보
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    meeting_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    meeting_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # HH:MM
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    channel: Mapped[MeetingChannel] = mapped_column(
        Enum(MeetingChannel),
        nullable=False,
        default=MeetingChannel.IN_PERSON,
    )
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus),
        nullable=False,
        default=MeetingStatus.COMPLETED,
    )

    # 회의록
    minutes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 제공 자료 목록 [{name, description?, url?}]
    provided_materials: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 첨부파일
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 마케팅 전용: 매수인 연결
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buyer_candidates.id"),
        nullable=True,
    )

    # 마케팅 전용: 조건 평가
    condition_match: Mapped[ConditionMatchLevel | None] = mapped_column(
        Enum(ConditionMatchLevel),
        nullable=True,
    )
    condition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 협상 전용: 관련 계약
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id"),
        nullable=True,
    )

    # 참석 인원 수 (비정규화, 빠른 조회용)
    attendee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 생성자
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
