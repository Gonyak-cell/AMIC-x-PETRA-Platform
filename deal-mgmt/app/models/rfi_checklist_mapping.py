"""RFI 아이템 ↔ 외부 체크리스트 매핑 모델."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RFIChecklistMapping(Base, TimestampMixin):
    """RFI 아이템 ↔ IM/FDD/DD 체크리스트 매핑."""

    __tablename__ = "rfi_checklist_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rfi_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("rfi_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    target_module: Mapped[str] = mapped_column(String(20), nullable=False)  # "IM", "FDD", "DD"
    target_checklist_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    target_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    target_field_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    synced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 관계
    rfi_item = relationship("RFIItem", back_populates="checklist_mappings")
