import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import NdaStatus, NdaType


class NDA(Base, TimestampMixin):
    """NDA — BuyerCandidate와 1:N 관계."""

    __tablename__ = "ndas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    buyer_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buyer_candidates.id"), nullable=False, index=True
    )
    nda_type: Mapped[NdaType] = mapped_column(Enum(NdaType), nullable=False, default=NdaType.MUTUAL)
    status: Mapped[NdaStatus] = mapped_column(Enum(NdaStatus), nullable=False, default=NdaStatus.DRAFT)
    sent_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    signed_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── AI 추출 필드 ────────────────────────────────────
    counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confidentiality_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
