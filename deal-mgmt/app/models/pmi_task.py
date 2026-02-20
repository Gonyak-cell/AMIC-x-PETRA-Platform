import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import PMICategory, PMIPriority, PMITaskStatus


class PMITask(Base, TimestampMixin):
    """PMI(Post-Merger Integration) 태스크 — Transaction과 1:N 관계."""

    __tablename__ = "pmi_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    category: Mapped[PMICategory] = mapped_column(Enum(PMICategory), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PMITaskStatus] = mapped_column(
        Enum(PMITaskStatus), nullable=False, default=PMITaskStatus.NOT_STARTED
    )
    priority: Mapped[PMIPriority] = mapped_column(Enum(PMIPriority), nullable=False, default=PMIPriority.MEDIUM)
    assignee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    assignee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    completed_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dependency_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
