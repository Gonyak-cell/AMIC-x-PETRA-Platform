import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.standard_line_item import FinancialStatement
from app.utils.db_types import JsonbColumn


class TieOutStatus(str, enum.Enum):
    """Tie-out 결과 상태."""

    PASS = "PASS"  # 허용 오차 이내
    FAIL = "FAIL"  # 허용 오차 초과
    WARNING = "WARNING"  # 미매핑 계정 존재하나 합계는 일치


class TieOutResult(Base):
    """IS/BS Tie-out 검증 결과 — FDD-303.

    TB 합계와 재구성 재무제표 합계를 비교하여
    일치 여부를 품질 게이트로 저장.
    """

    __tablename__ = "tie_out_result"

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

    # ── 검증 대상 ──
    statement_type: Mapped[FinancialStatement] = mapped_column(
        Enum(FinancialStatement), nullable=False, comment="재무제표 유형 (IS/BS)"
    )
    status: Mapped[TieOutStatus] = mapped_column(
        Enum(TieOutStatus), nullable=False, comment="검증 결과"
    )

    # ── 금액 비교 ──
    tb_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="TB 합계"
    )
    reconstructed_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="재구성 합계"
    )
    variance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="차이 금액"
    )
    variance_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, comment="차이 비율 (%)"
    )

    # ── 미매핑 현황 ──
    unmapped_account_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="미매핑 계정 수"
    )
    unmapped_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="미매핑 잔액 합계"
    )

    # ── 상세 불일치 (Top 20) ──
    top_discrepancies: Mapped[list | None] = mapped_column(
        JsonbColumn, nullable=True, comment="Top 20 불일치 계정 상세"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_tie_out_result_deal", "deal_id"),
        Index("ix_tie_out_result_snapshot", "snapshot_id"),
        Index("ix_tie_out_result_status", "status"),
    )
