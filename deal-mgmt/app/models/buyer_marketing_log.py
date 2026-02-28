"""매수자별 마케팅 활동 개별 로그 — Short-List 6단계 추적."""

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import MarketingStage


class BuyerMarketingLog(Base, TimestampMixin):
    """Short-List 매수자의 마케팅 활동 로그 (단계별 일자/내용 기록)."""

    __tablename__ = "buyer_marketing_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("buyer_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[MarketingStage] = mapped_column(Enum(MarketingStage), nullable=False)
    log_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
