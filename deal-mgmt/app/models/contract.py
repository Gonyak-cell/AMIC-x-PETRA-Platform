import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ContractStatus, ContractType, SignatureStatus


class Contract(Base, TimestampMixin):
    """계약서 — Transaction과 1:N 관계."""

    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True
    )
    contract_type: Mapped[ContractType] = mapped_column(Enum(ContractType), nullable=False, default=ContractType.SPA)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), nullable=False, default=ContractStatus.DRAFT
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    seller_signature: Mapped[SignatureStatus] = mapped_column(
        Enum(SignatureStatus), nullable=False, default=SignatureStatus.PENDING
    )
    buyer_signature: Mapped[SignatureStatus] = mapped_column(
        Enum(SignatureStatus), nullable=False, default=SignatureStatus.PENDING
    )
    ai_analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_risk_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
