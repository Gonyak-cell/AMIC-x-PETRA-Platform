import uuid

from sqlalchemy import Boolean, Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import TransactionPhase, TransactionSide, TransactionStatus


class Transaction(Base, TimestampMixin):
    """M&A 거래 — 7단계 워크플로우의 핵심 엔티티."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    side: Mapped[TransactionSide] = mapped_column(Enum(TransactionSide), nullable=False)
    phase: Mapped[TransactionPhase] = mapped_column(
        Enum(TransactionPhase), nullable=False, default=TransactionPhase.ENGAGEMENT
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), nullable=False, default=TransactionStatus.DRAFT
    )

    # Target
    target_company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_corp_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Client
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Financial
    estimated_deal_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")

    # Classification
    deal_structure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    investment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Team
    lead_advisor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_captain_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Dates
    target_close_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Service Links
    fdd_deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    im_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
