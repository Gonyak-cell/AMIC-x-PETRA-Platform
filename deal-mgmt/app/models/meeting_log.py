"""미팅 로그 — 마케팅/협상 단계 공용."""

import uuid

import sqlalchemy as sa
from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    ConditionMatchLevel,
    MarketingStage,
    MeetingChannel,
    MeetingPhase,
    MeetingStatus,
    MeetingType,
)


class MeetingLog(Base, TimestampMixin):
    """마케팅/협상 미팅 로그."""

    __tablename__ = "meeting_logs"
    __table_args__ = (sa.Index("ix_meeting_logs_txn_phase", "transaction_id", "meeting_phase"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
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
    meeting_type: Mapped[MeetingType | None] = mapped_column(
        Enum(MeetingType),
        nullable=True,
        default=None,
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
    provided_materials: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # 첨부파일
    attachments: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # 마케팅 전용: 매수인 연결
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("buyer_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 마케팅 전용: 마케팅 단계 연결 (통합 로그)
    marketing_stage: Mapped[MarketingStage | None] = mapped_column(
        Enum(MarketingStage),
        nullable=True,
        index=True,
    )

    # 마케팅 전용: 조건 평가
    condition_match: Mapped[ConditionMatchLevel | None] = mapped_column(
        Enum(ConditionMatchLevel),
        nullable=True,
    )
    condition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 협상 전용: 관련 계약
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("contracts.id"),
        nullable=True,
    )

    # 참석 인원 수 (비정규화, 빠른 조회용)
    attendee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 생성자
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
