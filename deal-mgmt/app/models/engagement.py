import uuid

from sqlalchemy import JSON, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import EngagementType


class Engagement(Base, TimestampMixin):
    """수임계약 — Transaction과 1:N 관계."""

    __tablename__ = "engagements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    type: Mapped[EngagementType] = mapped_column(Enum(EngagementType), nullable=False)
    counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fee_structure: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    signed_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    service_scope_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
