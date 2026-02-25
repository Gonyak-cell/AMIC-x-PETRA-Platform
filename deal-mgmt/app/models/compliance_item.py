"""컴플라이언스 체크리스트 항목."""

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ComplianceCategory, ComplianceStatus


class ComplianceItem(Base, TimestampMixin):
    """거래별 규제/컴플라이언스 체크리스트 항목."""

    __tablename__ = "compliance_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    category: Mapped[ComplianceCategory] = mapped_column(Enum(ComplianceCategory), nullable=False)
    requirement: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regulatory_body: Mapped[str | None] = mapped_column(String(200), nullable=True)
    assignee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.NOT_STARTED
    )
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    filing_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    permit_requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permit_requirements.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
