import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import BidStatus, BidType, ValuationMethod


class Bid(Base, TimestampMixin):
    """IOI / LOI / Final Offer — BuyerCandidate와 1:N 관계."""

    __tablename__ = "bids"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    buyer_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buyer_candidates.id"), nullable=False, index=True
    )
    bid_type: Mapped[BidType] = mapped_column(Enum(BidType), nullable=False)
    status: Mapped[BidStatus] = mapped_column(Enum(BidStatus), nullable=False, default=BidStatus.SUBMITTED)

    # Valuation
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    valuation_method: Mapped[ValuationMethod | None] = mapped_column(Enum(ValuationMethod), nullable=True)
    multiple: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Dates
    submitted_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    valid_until: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Details
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── AI 추출 필드 ────────────────────────────────────
    exclusivity_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conditions_precedent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
