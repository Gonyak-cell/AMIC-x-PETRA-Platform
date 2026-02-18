import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import EngagementType


class Engagement(Base, TimestampMixin):
    """수임계약 — Transaction과 1:N 관계."""

    __tablename__ = "engagements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    type: Mapped[EngagementType] = mapped_column(Enum(EngagementType), nullable=False)
    fee_structure: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    signed_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
