"""Net Debt 분석 모델 — EPIC-07 (FDD-701/702/703/704).

Net Debt 계산 결과, 개별 Debt/Cash 항목, Debt-like 후보를
스냅샷 단위로 저장.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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

# -- Enums -------------------------------------------------------


class DebtStatus(str, enum.Enum):
    """Net Debt 계산 상태."""

    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"


class DebtItemType(str, enum.Enum):
    """Net Debt 항목 유형 — FDD-701."""

    GROSS_DEBT = "GROSS_DEBT"  # 차입금 (단기/장기/사채 등)
    CASH = "CASH"  # 현금성 자산
    DEBT_LIKE = "DEBT_LIKE"  # 차입금 유사 항목 (리스부채, 충당부채 등)
    CASH_LIKE = "CASH_LIKE"  # 현금 유사 항목 (제한예금 등)


class DebtItemStatus(str, enum.Enum):
    """개별 Net Debt 항목 상태 — FDD-702."""

    CANDIDATE = "CANDIDATE"  # 자동 감지
    PROPOSED = "PROPOSED"  # 수동 제안
    APPROVED = "APPROVED"  # 승인
    REJECTED = "REJECTED"  # 거부


# -- Models -------------------------------------------------------


class NetDebtCalculation(Base):
    """Net Debt 계산 결과 — FDD-701.

    Net Debt = Gross Debt - Cash
    Adjusted Net Debt = Net Debt + Debt-like - Cash-like
    """

    __tablename__ = "net_debt_calculation"

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

    # -- Net Debt Summary (NUMERIC(18,4)) --
    gross_debt: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="총 차입금 (단기+장기+사채)",
    )
    cash_and_equivalents: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="현금 및 현금성자산",
    )
    net_debt: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Net Debt = Gross Debt - Cash",
    )
    debt_like_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="Debt-like 항목 합계",
    )
    cash_like_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="Cash-like 항목 합계",
    )
    adjusted_net_debt: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Adjusted Net Debt = Net Debt + Debt-like - Cash-like",
    )

    # -- Options (FDD-703, FDD-704) --
    include_lease_liabilities: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="IFRS 16 리스부채 포함 여부",
    )
    include_deferred_revenue: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="이연수익(선수금) debt-like 포함 여부",
    )

    # -- Balance Check --
    balance_check_error: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="GrossDebt - Cash + DebtLike - CashLike - AdjustedNetDebt; must be 0",
    )

    # -- Category Breakdown (JSON) --
    category_breakdown: Mapped[dict] = mapped_column(
        JsonbColumn,
        nullable=False,
        comment="DebtItemType별 상세 내역",
    )

    # -- Metadata --
    engine_version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="엔진 버전"
    )
    status: Mapped[DebtStatus] = mapped_column(
        Enum(DebtStatus),
        nullable=False,
        default=DebtStatus.DRAFT,
    )

    # -- Timestamps --
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # -- Relationships --
    items: Mapped[list["DebtItem"]] = relationship(
        back_populates="net_debt_calculation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_net_debt_calculation_deal", "deal_id"),
        Index("ix_net_debt_calculation_snapshot", "snapshot_id"),
    )


class DebtItem(Base):
    """Net Debt 개별 항목 — FDD-702.

    Gross Debt, Cash, Debt-like, Cash-like 개별 항목.
    자동 감지 또는 수동 추가.
    """

    __tablename__ = "debt_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    net_debt_calculation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("net_debt_calculation.id", ondelete="CASCADE"),
        nullable=False,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )

    # -- Item Details --
    item_type: Mapped[DebtItemType] = mapped_column(
        Enum(DebtItemType), nullable=False, comment="항목 유형"
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="항목 설명"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="금액 (양수=차입금/자산, 음수는 사용하지 않음)",
    )

    # -- Source Reference --
    source_account_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="원천 TB 계정코드"
    )
    source_account_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="원천 TB 계정명"
    )

    # -- Detection Metadata --
    detection_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        comment="감지 방법: auto_classification, lease_rule, deferred_revenue_rule, manual",
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="감지 신뢰도 (0-100)"
    )

    # -- Workflow --
    status: Mapped[DebtItemStatus] = mapped_column(
        Enum(DebtItemStatus),
        nullable=False,
        default=DebtItemStatus.CANDIDATE,
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

    # -- Timestamps --
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # -- Relationships --
    net_debt_calculation: Mapped["NetDebtCalculation"] = relationship(
        back_populates="items",
    )

    __table_args__ = (
        Index("ix_debt_item_calc", "net_debt_calculation_id"),
        Index("ix_debt_item_deal", "deal_id"),
        Index("ix_debt_item_status", "status"),
    )
