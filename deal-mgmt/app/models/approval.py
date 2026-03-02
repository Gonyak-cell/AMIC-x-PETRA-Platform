import uuid

from sqlalchemy import JSON, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ApprovalStatus, ApprovalType


class ApprovalRequest(Base, TimestampMixin):
    """승인 요청 — 단계 전환, 상태 변경, 계약 서명 등의 결재선."""

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    requester_email: Mapped[str] = mapped_column(String(255), nullable=False)
    approval_type: Mapped[ApprovalType] = mapped_column(Enum(ApprovalType), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    approvers: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    deadline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
