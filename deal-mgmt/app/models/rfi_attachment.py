"""RFI V2 첨부 파일 모델 — 증빙 자료 관리."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RFIAttachment(Base):
    """RFI 증빙 자료 — 스레드 또는 질의에 직접 연결."""

    __tablename__ = "rfi_attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("rfi_threads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    vdr_index: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    is_mapped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 관계
    thread = relationship("RFIThread", back_populates="attachments", foreign_keys=[thread_id])
    item = relationship("RFIItemV2", back_populates="attachments", foreign_keys=[item_id])
