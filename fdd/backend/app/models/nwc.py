"""NWC(Net Working Capital) 분석 모델 — EPIC-06 (FDD-601/602/603).

NWC 계산 결과, 개별 WC 항목, 월별 트렌드, Peg 시뮬레이션을
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
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.db_types import JsonbColumn

# -- Enums -------------------------------------------------------


class NWCStatus(str, enum.Enum):
    """NWC 계산 상태."""

    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"


class NWCClassification(str, enum.Enum):
    """NWC 항목 분류 — FDD-601."""

    ABOVE_LINE = "ABOVE_LINE"  # 정상 운전자본 (AR, Inventory, AP, Accruals)
    BELOW_LINE = "BELOW_LINE"  # 운전자본 외 (debt-like, cash-like)
    EXCLUDED = "EXCLUDED"  # 제외 항목


class PegMethod(str, enum.Enum):
    """Peg 산정 방법 — FDD-603."""

    LTM_AVERAGE = "LTM_AVERAGE"  # Last 12 Months 평균
    TTM = "TTM"  # Trailing Twelve Months (마지막월)
    LAST_MONTH = "LAST_MONTH"  # 직전월
    MAX = "MAX"  # 최댓값
    MIN = "MIN"  # 최솟값
    CUSTOM = "CUSTOM"  # 사용자 지정


# -- Models -------------------------------------------------------


class NWCCalculation(Base):
    """NWC 계산 결과 — FDD-602.

    BS 계정을 운전자본 항목으로 분류하고, 월별 트렌드 + Peg 산정.
    """

    __tablename__ = "nwc_calculation"

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

    # -- NWC Summary (NUMERIC(18,4)) --
    total_current_assets: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="WC 유동자산 합계 (Cash 제외)",
    )
    total_current_liabilities: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="WC 유동부채 합계 (Debt 제외)",
    )
    net_working_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="NWC = CA - CL",
    )

    # -- Peg --
    peg_method: Mapped[PegMethod] = mapped_column(
        Enum(PegMethod),
        nullable=False,
        default=PegMethod.LTM_AVERAGE,
        comment="Peg 산정 방법",
    )
    peg_target: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="Peg 목표 NWC",
    )
    peg_delta: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0"),
        comment="NWC at reference date - Peg target",
    )

    # -- Monthly Trend (JSON) --
    monthly_trend: Mapped[dict] = mapped_column(
        JsonbColumn,
        nullable=False,
        comment='월별 NWC 추이: {"2025-01": {"nwc": "...", "ca": "...", "cl": "..."}, ...}',
    )

    # -- Category Breakdown (JSON) --
    category_breakdown: Mapped[dict] = mapped_column(
        JsonbColumn,
        nullable=False,
        comment="LineItemCategory별 금액 상세",
    )

    # -- Metadata --
    engine_version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="엔진 버전"
    )
    status: Mapped[NWCStatus] = mapped_column(
        Enum(NWCStatus),
        nullable=False,
        default=NWCStatus.DRAFT,
    )

    # -- Timestamps --
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # -- Relationships --
    line_items: Mapped[list["NWCLineItem"]] = relationship(
        back_populates="nwc_calculation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_nwc_calculation_deal", "deal_id"),
        Index("ix_nwc_calculation_snapshot", "snapshot_id"),
    )


class NWCLineItem(Base):
    """NWC 개별 항목 — FDD-601.

    BS 계정의 WC 분류(ABOVE_LINE/BELOW_LINE/EXCLUDED) 및
    기준일 잔액 + 월별 잔액.
    """

    __tablename__ = "nwc_line_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nwc_calculation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nwc_calculation.id", ondelete="CASCADE"),
        nullable=False,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )

    # -- Item Details --
    account_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="원천 TB 계정코드"
    )
    account_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="원천 TB 계정명"
    )
    line_item_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="LineItemCategory value (AR, INVENTORY, AP, etc.)",
    )
    classification: Mapped[NWCClassification] = mapped_column(
        Enum(NWCClassification),
        nullable=False,
        default=NWCClassification.ABOVE_LINE,
        comment="ABOVE_LINE / BELOW_LINE / EXCLUDED",
    )

    # -- Amount at Reference Date --
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="기준일 잔액"
    )

    # -- Monthly Amounts (JSON) --
    monthly_amounts: Mapped[dict] = mapped_column(
        JsonbColumn,
        nullable=False,
        comment='월별 잔액: {"2025-01": "1234.5678", ...}',
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
    nwc_calculation: Mapped["NWCCalculation"] = relationship(
        back_populates="line_items",
    )

    __table_args__ = (
        Index("ix_nwc_line_item_calc", "nwc_calculation_id"),
        Index("ix_nwc_line_item_deal", "deal_id"),
    )
