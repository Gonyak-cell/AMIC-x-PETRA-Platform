"""GP(운용사) 프로파일 — MA_GP_v3.xlsx에서 추출한 GP 레벨 집계 데이터."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import JSON, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GpProfile(Base, TimestampMixin):
    """GP 프로파일 — 358개 GP의 약정/활동/투자분야 집계.

    PefFundRegistry와 GP명(normalized_name)으로 조인하여
    FI 추천 시 Tier 분류에 활용한다.
    """

    __tablename__ = "gp_profiles"
    __table_args__ = (
        Index("ix_gp_profiles_normalized_name", "normalized_name"),
        Index("ix_gp_profiles_min_threshold", "min_threshold"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    raw_name: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False)

    # Sheet 1: 약정 집계
    min_committed_capital: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True, comment="C열 최소약정분담액(억원)"
    )
    min_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True, comment="D열 최소 기준점(약정 분담 하한)"
    )
    max_committed_capital: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True, comment="E열 최대약정분담액(억원)"
    )
    total_pef_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="F열 전체 PEF수")
    recent_pef_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="G열 21-24년 PEF수")
    recent_committed_sum: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True, comment="H열 21-24년 약정분담합계(억원)"
    )
    total_committed_sum: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True, comment="I열 총약정 분담합계(억원)"
    )

    # Sheet 1: 연도별 활동 (J~M열)
    pef_count_2021: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pef_count_2022: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pef_count_2023: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pef_count_2024: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sheet 3: 연도별 활동 매트릭스 (2010~2024, JSON {year: count})
    yearly_pef_counts: Mapped[dict[str, int] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment='연도별 PEF 결성 건수 (시트3, 예: {"2010": 2, "2021": 3})',
    )

    # Sheet 1 N열: 투자분야/주요 포트폴리오 (파싱)
    portfolio_sectors: Mapped[list[str] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment="투자분야 키워드 리스트 (N열 파싱)",
    )
    portfolio_companies: Mapped[list[str] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment="투자기업명 리스트 (N열 파싱)",
    )
    portfolio_raw: Mapped[str | None] = mapped_column(Text, nullable=True, comment="N열 원문")
