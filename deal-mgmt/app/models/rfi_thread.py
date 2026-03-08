"""RFI V2 스레드 모델 — insert-only 답변/추가질의 이력."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RFIAuthorRole


class RFIThread(Base):
    """RFI 답변/추가질의 이력 — insert-only, UPDATE 금지."""

    __tablename__ = "rfi_threads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    round_num: Mapped[int] = mapped_column(Integer, nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    author_role: Mapped[RFIAuthorRole] = mapped_column(Enum(RFIAuthorRole), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 관계
    item = relationship("RFIItemV2", back_populates="threads")
    attachments: Mapped[list["RFIAttachment"]] = relationship(  # noqa: F821
        "RFIAttachment",
        back_populates="thread",
        lazy="selectin",
        foreign_keys="RFIAttachment.thread_id",
    )
