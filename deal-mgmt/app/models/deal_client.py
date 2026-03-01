"""DealClient — 외부 고객의 딜 접근 매핑."""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DealClient(Base, TimestampMixin):
    """CLIENT 역할 사용자가 열람할 수 있는 거래를 매핑한다."""

    __tablename__ = "deal_clients"
    __table_args__ = (UniqueConstraint("transaction_id", "email", name="uq_deal_client_txn_email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("transactions.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    added_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
