"""협상 이견 추적 — 우리측/상대측/법률검토 입장 + AI 조항 제안."""

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import NegotiationIssuePriority, NegotiationIssueStatus


class NegotiationIssue(Base, TimestampMixin):
    """협상 이견 — 다자 입장 추적 및 AI 조항 수정 제안."""

    __tablename__ = "negotiation_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meeting_logs.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    # 이견 식별
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    clause_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)  # e.g. "SPA 4.2조"
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "가격", "진술보증"

    # 다자 입장
    our_position: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterpart_position: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_review: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI 생성 조항 수정 제안
    ai_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_suggestion_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 상태
    status: Mapped[NegotiationIssueStatus] = mapped_column(
        Enum(NegotiationIssueStatus), nullable=False, default=NegotiationIssueStatus.OPEN,
    )
    priority: Mapped[NegotiationIssuePriority] = mapped_column(
        Enum(NegotiationIssuePriority), nullable=False, default=NegotiationIssuePriority.MEDIUM,
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
