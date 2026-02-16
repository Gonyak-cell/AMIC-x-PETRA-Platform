"""환율 모델 — Sprint 16 (멀티 통화 지원).

딜별 환율을 관리한다. BS 항목에는 기말환율(CLOSING),
IS 항목에는 평균환율(AVERAGE)을 적용.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RateType(str, enum.Enum):
    """환율 유형."""

    CLOSING = "CLOSING"  # 기말환율 (BS 항목)
    AVERAGE = "AVERAGE"  # 평균환율 (IS 항목)
    HISTORICAL = "HISTORICAL"  # 역사적환율 (자본 항목)


class RateSource(str, enum.Enum):
    """환율 출처."""

    MANUAL = "MANUAL"  # 사용자 입력
    API = "API"  # 외부 API (향후)
    CALCULATED = "CALCULATED"  # 계산 (교차환율 등)


class ExchangeRate(Base):
    """딜별 환율.

    동일 딜 내에서 통화쌍 + 유형 + 기준일 조합은 고유.
    """

    __tablename__ = "exchange_rate"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="원화 통화코드 (예: USD)"
    )
    to_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="대상 통화코드 (예: KRW)"
    )
    rate_type: Mapped[RateType] = mapped_column(
        Enum(RateType), nullable=False, comment="환율 유형"
    )
    rate: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="환율 (최대 4자리)"
    )
    effective_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="적용 기준일"
    )
    period_key: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
        comment="기간 키 (AVERAGE용, 예: 2025-01)",
    )
    source: Mapped[RateSource] = mapped_column(
        Enum(RateSource),
        nullable=False,
        default=RateSource.MANUAL,
    )
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_exchange_rate_deal", "deal_id"),
        UniqueConstraint(
            "deal_id",
            "from_currency",
            "to_currency",
            "rate_type",
            "effective_date",
            name="uq_exchange_rate",
        ),
    )
