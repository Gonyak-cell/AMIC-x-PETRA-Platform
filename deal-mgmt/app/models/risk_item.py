"""리스크 레지스터 항목."""

import uuid

from sqlalchemy import Enum, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import RiskCategory, RiskLikelihood, RiskSeverity, RiskStatus


class RiskItem(Base, TimestampMixin):
    """거래별 리스크 항목 — 5x4 리스크 매트릭스 지원."""

    __tablename__ = "risk_items"
    __table_args__ = (Index("ix_risk_items_txn_sev_status", "transaction_id", "severity", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
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
