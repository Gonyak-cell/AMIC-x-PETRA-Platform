"""미팅 액션아이템 / 요청사항."""

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ActionItemStatus, NegotiationIssuePriority


class MeetingActionItem(Base, TimestampMixin):
    """미팅에서 발생한 액션아이템/요청사항."""

    __tablename__ = "meeting_action_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("meeting_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    status: Mapped[ActionItemStatus] = mapped_column(
        Enum(ActionItemStatus),
        nullable=False,
        default=ActionItemStatus.PENDING,
    )
    priority: Mapped[NegotiationIssuePriority | None] = mapped_column(
        Enum(NegotiationIssuePriority),
        nullable=True,
    )
