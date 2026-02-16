import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.db_types import JsonbColumn


class FinancialStatement(str, enum.Enum):
    """재무제표 유형."""

    IS = "IS"  # Income Statement (손익계산서)
    BS = "BS"  # Balance Sheet (재무상태표)


class LineItemCategory(str, enum.Enum):
    """표준 라인아이템 분류."""

    # ── Income Statement ──
    REVENUE = "REVENUE"
    COGS = "COGS"
    SGA = "SGA"
    OTHER_OPERATING_INCOME = "OTHER_OPERATING_INCOME"
    DEPRECIATION_AMORTIZATION = "DEPRECIATION_AMORTIZATION"
    NON_OPERATING = "NON_OPERATING"
    INTEREST_EXPENSE = "INTEREST_EXPENSE"
    INTEREST_INCOME = "INTEREST_INCOME"
    TAX_EXPENSE = "TAX_EXPENSE"

    # ── Balance Sheet: Assets ──
    CASH = "CASH"
    AR = "AR"
    INVENTORY = "INVENTORY"
    OTHER_CURRENT_ASSETS = "OTHER_CURRENT_ASSETS"
    PPE = "PPE"
    INTANGIBLES = "INTANGIBLES"
    OTHER_NONCURRENT_ASSETS = "OTHER_NONCURRENT_ASSETS"

    # ── Balance Sheet: Liabilities ──
    AP = "AP"
    ACCRUALS = "ACCRUALS"
    OTHER_CURRENT_LIABILITIES = "OTHER_CURRENT_LIABILITIES"
    DEBT = "DEBT"
    LEASE_LIABILITIES = "LEASE_LIABILITIES"
    OTHER_NONCURRENT_LIABILITIES = "OTHER_NONCURRENT_LIABILITIES"

    # ── Balance Sheet: Equity ──
    EQUITY = "EQUITY"


class StandardLineItem(Base):
    """표준 라인아이템(CoA Canon) — FDD-301.

    FDD에서 사용하는 80개 표준 계정 분류 체계.
    매핑 엔진이 원천 계정명을 이 표준 항목에 대응시킴.
    """

    __tablename__ = "standard_line_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="표준 코드 (예: IS-REV-001)"
    )
    name_en: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="영문 명칭"
    )
    name_ko: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="한글 명칭"
    )
    category: Mapped[LineItemCategory] = mapped_column(
        Enum(LineItemCategory), nullable=False, comment="분류 카테고리"
    )
    statement_type: Mapped[FinancialStatement] = mapped_column(
        Enum(FinancialStatement), nullable=False, comment="재무제표 유형 (IS/BS)"
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="표시 순서"
    )
    parent_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="상위 항목 코드 (계층 구조)"
    )
    is_subtotal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="소계/합계 행 여부"
    )
    keywords: Mapped[list | None] = mapped_column(
        JsonbColumn,
        nullable=True,
        comment='매핑용 키워드 목록 (예: ["매출", "수익", "sales"])',
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
