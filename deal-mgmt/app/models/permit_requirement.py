"""개별 인허가 요건 항목."""

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import PermitFilingType, PermitRequirementStatus, PermitTimingType


class PermitRequirement(Base, TimestampMixin):
    """개별 인허가 요건 항목."""

    __tablename__ = "permit_requirements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("permit_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )
    # 인허가 정보
    permit_name: Mapped[str] = mapped_column(String(300), nullable=False)
    regulatory_body: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 신고/허가 유형
    filing_type: Mapped[PermitFilingType] = mapped_column(Enum(PermitFilingType), nullable=False)
    timing_type: Mapped[PermitTimingType] = mapped_column(Enum(PermitTimingType), nullable=False)
    # 기한
    pre_filing_deadline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    post_filing_deadline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculated_deadline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # 필요 서류
    required_documents: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # 상태 추적
    status: Mapped[PermitRequirementStatus] = mapped_column(
        Enum(PermitRequirementStatus),
        nullable=False,
        default=PermitRequirementStatus.IDENTIFIED,
    )
    # KB 출처 vs LLM 출처
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="KB")
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    # 연결
    compliance_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("compliance_items.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
