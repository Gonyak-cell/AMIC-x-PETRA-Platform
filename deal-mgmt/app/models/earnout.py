import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import EarnoutMetric, EarnoutStatus


class EarnoutMilestone(Base, TimestampMixin):
    """어닝아웃 마일스톤 — Transaction과 1:N 관계."""

    __tablename__ = "earnout_milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric: Mapped[EarnoutMetric] = mapped_column(Enum(EarnoutMetric), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    actual_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="KRW")
    measurement_start: Mapped[str | None] = mapped_column(String(10), nullable=True)
    measurement_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    payment_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    payment_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[EarnoutStatus] = mapped_column(Enum(EarnoutStatus), nullable=False, default=EarnoutStatus.PENDING)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
