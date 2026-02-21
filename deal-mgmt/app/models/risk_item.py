"""리스크 레지스터 항목."""

import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import RiskCategory, RiskLikelihood, RiskSeverity, RiskStatus


class RiskItem(Base, TimestampMixin):
    """거래별 리스크 항목 — 5x4 리스크 매트릭스 지원."""

    __tablename__ = "risk_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    category: Mapped[RiskCategory] = mapped_column(Enum(RiskCategory), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[RiskSeverity] = mapped_column(Enum(RiskSeverity), nullable=False, default=RiskSeverity.MEDIUM)
    likelihood: Mapped[RiskLikelihood] = mapped_column(
        Enum(RiskLikelihood), nullable=False, default=RiskLikelihood.MEDIUM
    )
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mitigation_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RiskStatus] = mapped_column(Enum(RiskStatus), nullable=False, default=RiskStatus.IDENTIFIED)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
