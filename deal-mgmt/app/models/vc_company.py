"""Value Chain 기업 — MA_ValueChain_v7.xlsx Sheet 2 기업개황 (114,964개)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VcCompany(Base, TimestampMixin):
    """Value Chain 기업 레퍼런스 (경량 조회 전용).

    기존 SICompany(168컬럼, DART enrichment용)와 별개로,
    114,964개 기업의 업종 분류 + 매출 기반 SI 후보 필터링에 사용한다.
    """

    __tablename__ = "vc_companies"
    __table_args__ = (
        Index("ix_vc_companies_industry", "industry_name"),
        Index("ix_vc_companies_io_sector", "io_sector_code"),
        Index("ix_vc_companies_revenue", "revenue"),
        Index("ix_vc_companies_name", "company_name"),
        Index("ix_vc_companies_industry_revenue", "industry_name", "revenue"),
        Index("ix_vc_companies_io_sector_name_revenue", "io_sector_name", "revenue"),
        Index("ix_vc_companies_io_sector_name", "io_sector_name"),
        # corp_reg_no, biz_reg_no: 063 마이그레이션에서 expression index로 관리
        # (REPLACE(REPLACE(col, '-', ''), ' ', '') 패턴)
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False)
    english_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    disclosure_name: Mapped[str | None] = mapped_column(String(300), nullable=True, comment="공시회사명")
    listing_code: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="종목코드 (미상장=NULL)")
    ceo_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    corp_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="유가증권시장/코스닥시장/기타법인")
    corp_reg_no: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="법인등록번호")
    biz_reg_no: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="사업자등록번호")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # 핵심 분류 필드
    industry_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="업종명 (1,574 고유값, 계수표 매칭)"
    )
    io_sector_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="IO부문코드 (1-83)")
    io_sector_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="IO부문명 (81 고유값)")

    founded_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fiscal_month: Mapped[str | None] = mapped_column(String(5), nullable=True, comment="결산월")

    # DART 연동 (점진적 enrichment)
    corp_code: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="DART 고유번호")
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="매출액(억원)")
    operating_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="영업이익(억원)")
    net_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="당기순이익(억원)")
    total_assets: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="자산총계(억원)")
    total_debt: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="부채총계(억원)")
    total_equity: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="자본총계(억원)")
    capital: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True, comment="자본금(억원)")
    debt_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="부채비율(%)")
    revenue_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="재무정보 기준연도")
