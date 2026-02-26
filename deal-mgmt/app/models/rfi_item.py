"""RFI 개별 질문/응답 항목 모델."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RFICategory, RFIItemPriority, RFIItemStatus, RFISourceType


class RFIItem(Base, TimestampMixin):
    """RFI 개별 질문/응답 항목."""

    __tablename__ = "rfi_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfis.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 질문
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[RFICategory] = mapped_column(Enum(RFICategory), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[RFIItemPriority] = mapped_column(
        Enum(RFIItemPriority), nullable=False, default=RFIItemPriority.MEDIUM
    )

    # 응답
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_documents: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 검토자 의견
    reviewer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 상태
    status: Mapped[RFIItemStatus] = mapped_column(
        Enum(RFIItemStatus), nullable=False, default=RFIItemStatus.PENDING
    )
    assignee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # 원천 추적
    source_type: Mapped[RFISourceType] = mapped_column(
        Enum(RFISourceType), nullable=False, default=RFISourceType.MANUAL
    )
    source_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_ref_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # VDR 연결
    vdr_document_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 메모
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_question: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 관계
    rfi = relationship("RFI", back_populates="items")
    checklist_mappings = relationship(
        "RFIChecklistMapping", back_populates="rfi_item", cascade="all, delete-orphan", lazy="selectin"
    )
