"""RFI (Request for Information) 라운드 모델."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RFIStatus


class RFI(Base, TimestampMixin):
    """RFI 라운드 — 거래별 정보 요청 묶음."""

    __tablename__ = "rfis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RFIStatus] = mapped_column(Enum(RFIStatus), nullable=False, default=RFIStatus.DRAFT)

    # 수신자 정보
    recipient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_company: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 기한
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 집계 (비정규화)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    responded_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 메타
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 관계
    items = relationship("RFIItem", back_populates="rfi", cascade="all, delete-orphan", lazy="selectin")
