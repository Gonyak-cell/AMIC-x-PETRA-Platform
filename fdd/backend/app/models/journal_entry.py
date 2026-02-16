import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.db_types import JsonbColumn


class JournalEntry(Base):
    __tablename__ = "journal_entry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_file.id", ondelete="CASCADE"),
        nullable=False,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Common fields
    account_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Amount fields — DECIMAL(18,4) mandatory
    debit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    credit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # GL-specific
    entry_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    line_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Type-specific overflow
    extra_data: Mapped[dict | None] = mapped_column(JsonbColumn, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    upload_file: Mapped["UploadFile"] = relationship(  # noqa: F821
        back_populates="journal_entries"
    )

    __table_args__ = (
        Index("ix_journal_entry_deal", "deal_id"),
        Index("ix_journal_entry_upload", "upload_file_id"),
        Index("ix_journal_entry_account", "account_code"),
        Index("ix_journal_entry_date", "entry_date"),
        Index("ix_journal_entry_entry_id", "entry_id"),
        Index("ix_journal_entry_entity", "entity_id"),
    )
