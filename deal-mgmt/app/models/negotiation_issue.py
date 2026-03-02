"""협상 이견 추적 — 우리측/상대측/법률검토 입장 + AI 조항 제안."""

import uuid

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import IssueDecisionStatus, NegotiationIssuePriority, NegotiationIssueStatus


class NegotiationIssue(Base, TimestampMixin):
    """협상 이견 — 다자 입장 추적 및 AI 조항 수정 제안."""

    __tablename__ = "negotiation_issues"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("meeting_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
        Enum(NegotiationIssueStatus),
        nullable=False,
        default=NegotiationIssueStatus.OPEN,
    )
    priority: Mapped[NegotiationIssuePriority] = mapped_column(
        Enum(NegotiationIssuePriority),
        nullable=False,
        default=NegotiationIssuePriority.MEDIUM,
    )
    decision_status: Mapped[IssueDecisionStatus] = mapped_column(
        Enum(IssueDecisionStatus),
        nullable=False,
        default=IssueDecisionStatus.PENDING,
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # 교차 계약 연동
    linked_issue_ids: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    markup_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
