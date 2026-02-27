"""SI(전략적 투자자) 기업 레퍼런스 모델."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin


class SICompany(Base, TimestampMixin):
    """전략적 투자자 후보 기업 — KSIC 코드 기반 산업 분류 보유."""

    __tablename__ = "si_companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    jurir_no: Mapped[str | None] = mapped_column(
        String(13),
        unique=True,
        index=True,
        nullable=True,
        comment="법인등록번호 13자리 (하이픈 제거)",
    )
    corp_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="사업자등록번호 (하이픈 제거)",
    )
    ksic_codes: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    revenue_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="매출액 기준 사업연도 (예: 2024)",
    )
    has_investment_history: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
