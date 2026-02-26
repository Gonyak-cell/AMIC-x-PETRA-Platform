"""미팅 참석자."""

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import AttendeeRole, BuyerReaction


class MeetingAttendee(Base, TimestampMixin):
    """미팅 참석자 — 역할 및 반응(마케팅) 포함."""

    __tablename__ = "meeting_attendees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meeting_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[AttendeeRole] = mapped_column(
        Enum(AttendeeRole),
        nullable=False,
        default=AttendeeRole.OTHER,
    )

    # 마케팅 전용: 매수인 반응·코멘트
    reaction: Mapped[BuyerReaction | None] = mapped_column(Enum(BuyerReaction), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
