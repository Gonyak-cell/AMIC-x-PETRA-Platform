import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import WorkingGroupRole


class WorkingGroupMember(Base, TimestampMixin):
    """워킹그룹 멤버 — Transaction과 N:1 관계."""

    __tablename__ = "working_group_members"
    __table_args__ = (UniqueConstraint("transaction_id", "email", name="uq_wg_transaction_email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[WorkingGroupRole] = mapped_column(Enum(WorkingGroupRole), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
