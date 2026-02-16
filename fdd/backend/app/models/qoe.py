"""QoE(Adjusted EBITDA) 계산 모델 — EPIC-05 (FDD-501/502/503).

Reported EBITDA, Adjusted EBITDA, 조정항목(Bridge) 등을
스냅샷 단위로 저장.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
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

# ── Enums ────────────────────────────────────────────────


class QoEStatus(str, enum.Enum):
    """QoE 계산 상태."""

    DRAFT = "DRAFT"  # 초기 계산 결과
    REVIEW = "REVIEW"  # 검토 중
    APPROVED = "APPROVED"  # 승인됨


class AdjustmentCategory(str, enum.Enum):
    """조정항목 분류."""

    NON_RECURRING = "NON_RECURRING"  # 비경상항목 (소송, 구조조정 등)
    NON_OPERATING = "NON_OPERATING"  # 영업외항목 (외환, 이자 등)
    NORMALIZATION = "NORMALIZATION"  # 정상화 조정 (일회성 비용 제거)
    OWNER_RELATED = "OWNER_RELATED"  # 오너 관련 (과다 급여, 개인비용)
    PRO_FORMA = "PRO_FORMA"  # 프로포마 (인수 후 변경 반영)


class AdjustmentStatus(str, enum.Enum):
    """조정항목 상태."""

    CANDIDATE = "CANDIDATE"  # 자동 감지 후보
    PROPOSED = "PROPOSED"  # 사용자/분석가 제안
    APPROVED = "APPROVED"  # 승인됨
    REJECTED = "REJECTED"  # 거부됨


# ── Models ───────────────────────────────────────────────


class QoECalculation(Base):
    """QoE(Adjusted EBITDA) 계산 결과 — FDD-501.

    Reported EBITDA, Adjusted EBITDA, category breakdown, bridge 등을
    스냅샷 단위로 저장.
    """

    __tablename__ = "qoe_calculation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal_snapshot.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Core EBITDA Amounts (모두 NUMERIC(18,4)) ──
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="매출액 (P&L 양수)"
    )
    cogs: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="매출원가"
    )
    gross_profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="매출총이익"
    )
    sga: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="판관비"
    )
    depreciation_amortization: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="감가상각비 + 무형자산상각비"
    )
    other_operating: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="기타영업손익"
    )
    operating_income: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="영업이익"
    )
    reported_ebitda: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="Reported EBITDA"
    )
    total_adjustments: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="조정항목 합계",
    )
    adjusted_ebitda: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="Adjusted EBITDA"
    )

    # ── Balance Check ──
    balance_check_error: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="Reported + Σ(Adjustments) - Adjusted; must be 0.0000",
    )

    # ── Category Breakdown (JSON) ──
    category_breakdown: Mapped[dict] = mapped_column(
        JsonbColumn,
        nullable=False,
        comment="LineItemCategory별 금액 상세",
    )

    # ── Metadata ──
    engine_version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="엔진 버전"
    )
    status: Mapped[QoEStatus] = mapped_column(
        Enum(QoEStatus),
        nullable=False,
        default=QoEStatus.DRAFT,
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──
    adjustments: Mapped[list["AdjustmentItem"]] = relationship(
        back_populates="qoe_calculation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_qoe_calculation_deal", "deal_id"),
        Index("ix_qoe_calculation_snapshot", "snapshot_id"),
    )


class AdjustmentItem(Base):
    """QoE Bridge 조정항목 — FDD-502.

    Reported EBITDA → (조정항목 리스트) → Adjusted EBITDA 브리지의 개별 항목.
    """

    __tablename__ = "adjustment_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    qoe_calculation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qoe_calculation.id", ondelete="CASCADE"),
        nullable=False,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Adjustment Details ──
    category: Mapped[AdjustmentCategory] = mapped_column(
        Enum(AdjustmentCategory), nullable=False, comment="조정 분류"
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="조정 항목 설명"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="조정 금액 (양수=가산, 음수=차감)",
    )

    # ── Detection Metadata ──
    detection_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        comment="감지 방법: keyword, non_operating, year_end, large_entry, manual",
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="감지 신뢰도 (0-100)"
    )

    # ── Source Reference ──
    source_account_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="원천 TB 계정코드"
    )
    source_account_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="원천 TB 계정명"
    )
    source_entry_ids: Mapped[list | None] = mapped_column(
        JsonbColumn, nullable=True, comment="관련 GL 전표 ID 목록"
    )

    # ── Workflow ──
    status: Mapped[AdjustmentStatus] = mapped_column(
        Enum(AdjustmentStatus),
        nullable=False,
        default=AdjustmentStatus.CANDIDATE,
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="승인자"
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="승인 시각"
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="거부 사유"
    )

    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="표시 순서"
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──
    qoe_calculation: Mapped["QoECalculation"] = relationship(
        back_populates="adjustments",
    )

    __table_args__ = (
        Index("ix_adjustment_item_qoe", "qoe_calculation_id"),
        Index("ix_adjustment_item_deal", "deal_id"),
        Index("ix_adjustment_item_status", "status"),
    )
