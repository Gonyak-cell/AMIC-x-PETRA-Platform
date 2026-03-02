import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ClosingCategory, ClosingConditionStatus


class ClosingChecklist(Base, TimestampMixin):
    """Closing 체크리스트 — Transaction과 1:N 관계."""

    __tablename__ = "closing_checklists"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    category: Mapped[ClosingCategory] = mapped_column(Enum(ClosingCategory), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClosingConditionStatus] = mapped_column(
        Enum(ClosingConditionStatus), nullable=False, default=ClosingConditionStatus.PENDING
    )
    responsible_party: Mapped[str | None] = mapped_column(String(200), nullable=True)
    responsible_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    completed_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
