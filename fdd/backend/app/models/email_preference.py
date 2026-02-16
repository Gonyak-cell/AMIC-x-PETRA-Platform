"""Email notification preference model — Phase 5 Portal endpoints."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailPreference(Base):
    __tablename__ = "email_preference"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    deal_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    watchlist_alerts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    im_completion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
