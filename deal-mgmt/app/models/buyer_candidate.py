import uuid
from decimal import Decimal

from sqlalchemy import JSON, Enum, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import BuyerCandidateStatus, BuyerTier, BuyerType, DealRole


class BuyerCandidate(Base, TimestampMixin):
    """매수자 후보 — 14단계 상태 파이프라인."""

    __tablename__ = "buyer_candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    buyer_type: Mapped[BuyerType] = mapped_column(Enum(BuyerType), nullable=False)
    status: Mapped[BuyerCandidateStatus] = mapped_column(
        Enum(BuyerCandidateStatus), nullable=False, default=BuyerCandidateStatus.IDENTIFIED
    )

    # Tier & DART
    tier: Mapped[BuyerTier | None] = mapped_column(Enum(BuyerTier), nullable=True)
    corp_code: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Financial
    ioi_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    ioi_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    loi_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    loi_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    final_offer_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Notes
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Deal Role (컨소시엄 구조)
    deal_role: Mapped[DealRole | None] = mapped_column(Enum(DealRole), nullable=True, default=None)

    extra_data: Mapped[dict | None] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )
