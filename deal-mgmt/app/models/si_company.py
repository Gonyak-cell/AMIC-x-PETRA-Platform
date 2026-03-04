"""SI(전략적 투자자) 기업 레퍼런스 모델."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, Uuid
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
        comment="DART 기업 고유번호 (8자리)",
    )
    ksic_codes: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    revenue: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        index=True,
        comment="매출액(원, KRW), 예: 10_000_000_000 = 100억원",
    )
    revenue_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="매출액 기준 사업연도 (예: 2024)",
    )

    # ── 재무정보 (금융위 getSummFinaStat_V2) ──
    operating_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="영업이익 (enpBzopPft)",
    )
    net_income: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="당기순이익 (enpCrtmNpf)",
    )
    total_assets: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="자산총계 (enpTastAmt)",
    )
    total_debt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="부채총계 (enpTdbtAmt)",
    )
    total_equity: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="자본총계 (enpTcptAmt)",
    )
    capital_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="자본금 (enpCptlAmt)",
    )
    debt_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="부채비율 % (fnclDebtRto)",
    )
    pretax_income: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="법인세차감전순이익 (iclsPalClcAmt)",
    )
    fina_base_date: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="재무정보 기준일자 YYYYMMDD (basDt)",
    )
    fina_report_code: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="회계보고서 구분코드 (fnclDcd)",
    )
    fina_report_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="회계보고서 구분명 (fnclDcdNm)",
    )
    fina_stat_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="재무정보 최종 동기화 시점",
    )

    has_investment_history: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 기업기본정보 (금융위 getCorpOutline_V2) ──
    representative: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="대표자 (enpRprFnm)",
    )
    founded_date: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="설립일 YYYYMMDD (enpEstbDt)",
    )
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="기본주소 (enpBsadr)",
    )
    homepage: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="홈페이지 URL (enpHmpgUrl)",
    )
    employee_count: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="종업원수 (enpEmpeCnt)",
    )
    industry_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="업종명 (sicNm)",
    )
    main_business: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="주요사업 (enpMainBizNm)",
    )
    market_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="시장구분 P:유가 K:코스닥 N:코넥스 E:기타",
    )
    market_type_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="시장구분명 (corpRegMrktDcdNm)",
    )
    corp_basic_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="기업기본정보 최종 동기화 시점",
    )
    corp_basic_base_date: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="기본정보 기준일자 YYYYMMDD (basDt)",
    )
