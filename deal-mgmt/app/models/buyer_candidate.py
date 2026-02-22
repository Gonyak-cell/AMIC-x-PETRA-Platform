import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import BuyerCandidateStatus, BuyerType


class BuyerCandidate(Base, TimestampMixin):
    """매수자 후보 — 14단계 상태 파이프라인."""

    __tablename__ = "buyer_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    buyer_type: Mapped[BuyerType] = mapped_column(Enum(BuyerType), nullable=False)
    status: Mapped[BuyerCandidateStatus] = mapped_column(
        Enum(BuyerCandidateStatus), nullable=False, default=BuyerCandidateStatus.IDENTIFIED
    )

    # Financial
    ioi_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    ioi_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    loi_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    loi_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    final_offer_value: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Notes
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)
