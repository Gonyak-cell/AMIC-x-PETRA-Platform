"""포트폴리오 생존분석 모델

투자사의 피투자사(포트폴리오 기업)에 대한 생존 상태를 추적한다.
DART 감사보고서 제출 여부, 해산/폐업 공시 감지, 유니콘 등극 등을 분석한다.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SurvivalStatus(StrEnum):
    """포트폴리오 기업 생존 상태"""

    ACTIVE = "active"  # 정상 영업 (감사보고서 확인)
    AUDIT_MISSING = "audit_missing"  # 감사보고서 미제출
    DISSOLVED = "dissolved"  # 해산/폐업/청산
    UNICORN = "unicorn"  # 유니콘 등극 (기업가치 1조원 이상)
    UNKNOWN = "unknown"  # 미확인


# 상태 표시명 매핑
STATUS_DISPLAY_NAMES = {
    SurvivalStatus.ACTIVE: "정상",
    SurvivalStatus.AUDIT_MISSING: "감사보고서 미제출",
    SurvivalStatus.DISSOLVED: "해산/폐업",
    SurvivalStatus.UNICORN: "유니콘",
    SurvivalStatus.UNKNOWN: "미확인",
}


class PortfolioCompany(TimestampMixin, Base):
    """포트폴리오 기업 (투자사의 피투자사 생존분석)"""

    __tablename__ = "portfolio_companies"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 투자사 정보
    investor_company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        comment="투자사(GP) 기업 ID",
    )

    # 피투자사 정보
    target_company_name: Mapped[str] = mapped_column(String(300), index=True, comment="피투자사명")
    target_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="피투자사 기업 ID (식별된 경우)",
    )

    # 딜 연결
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"),
        index=True,
        comment="관련 딜 ID",
    )

    # 생존 상태
    survival_status: Mapped[str] = mapped_column(
        String(20), default="unknown", index=True, comment="생존 상태 (active/audit_missing/dissolved/unicorn/unknown)"
    )

    # 감사보고서 정보
    last_audit_date: Mapped[date | None] = mapped_column(Date, comment="최근 감사보고서 접수일")
    last_audit_rcept_no: Mapped[str | None] = mapped_column(String(20), comment="최근 감사보고서 접수번호")

    # 해산/폐업 정보
    dissolution_date: Mapped[date | None] = mapped_column(Date, comment="해산/폐업 공시일")
    dissolution_rcept_no: Mapped[str | None] = mapped_column(String(20), comment="해산/폐업 공시 접수번호")

    # 기업가치 및 유니콘 여부
    estimated_valuation: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="추정 기업가치 (원)")
    is_unicorn: Mapped[bool] = mapped_column(Boolean, default=False, comment="유니콘 여부 (기업가치 1조원 이상)")

    # 확인 이력
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="마지막 생존 확인 시각")
    notes: Mapped[str | None] = mapped_column(Text, comment="비고")

    # 관계
    investor_company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[investor_company_id]
    )
    target_company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[target_company_id]
    )
    deal: Mapped["Deal | None"] = relationship()  # noqa: F821
