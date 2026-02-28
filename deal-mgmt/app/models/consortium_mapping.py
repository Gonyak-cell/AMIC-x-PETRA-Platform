"""컨소시엄/공동투자 매핑 — 동일 딜 내 매수자 간 N:M 관계."""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ConsortiumStatus


class ConsortiumMapping(Base, TimestampMixin):
    """Lead ↔ Co-investor 컨소시엄 매핑."""

    __tablename__ = "consortium_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_buyer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    co_investor_buyer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ConsortiumStatus] = mapped_column(
        Enum(ConsortiumStatus), nullable=False, default=ConsortiumStatus.TAPPING
    )
    equity_share_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "lead_buyer_id != co_investor_buyer_id",
            name="ck_no_self_consortium",
        ),
        UniqueConstraint(
            "transaction_id",
            "lead_buyer_id",
            "co_investor_buyer_id",
            name="uq_consortium_pair_per_txn",
        ),
    )
