import uuid
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Enum, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import DealType, TransactionPhase, TransactionSide, TransactionStatus


class Transaction(Base, TimestampMixin):
    """M&A 거래 — 7단계 워크플로우의 핵심 엔티티."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    deal_type: Mapped[DealType] = mapped_column(Enum(DealType), nullable=False, default=DealType.SE)
    side: Mapped[TransactionSide] = mapped_column(Enum(TransactionSide), nullable=False)
    phase: Mapped[TransactionPhase] = mapped_column(
        Enum(TransactionPhase), nullable=False, default=TransactionPhase.ENGAGEMENT
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), nullable=False, default=TransactionStatus.DRAFT
    )

    # Target
    target_company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_corp_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Client
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Financial
    estimated_deal_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")

    # Classification
    deal_structure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    investment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Team
    lead_advisor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_captain_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Dates
    target_close_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Service Links
    fdd_deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    im_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # ── Deal Terms (거래 조건) ────────────────────────────
    sale_process: Mapped[str | None] = mapped_column(String(30), nullable=True)
    control_transfer: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_stake: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    new_share_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    old_share_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    valuation_basis: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cross_border: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_buyer_types: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    exclusivity: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    exclusivity_deadline: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── AI 추출 필드 ────────────────────────────────────
    corporate_info: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    financial_summary: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
