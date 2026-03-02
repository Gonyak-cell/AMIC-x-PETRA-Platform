import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import DDChecklistStatus, DDWorkstream


class DDChecklist(Base, TimestampMixin):
    """DD 워크스트림별 체크리스트 항목."""

    __tablename__ = "dd_checklists"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    workstream: Mapped[DDWorkstream] = mapped_column(Enum(DDWorkstream), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[DDChecklistStatus] = mapped_column(
        Enum(DDChecklistStatus), nullable=False, default=DDChecklistStatus.NOT_STARTED
    )
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
