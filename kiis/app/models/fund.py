from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Fund(TimestampMixin, Base):
    """펀드 모델 (VC/PEF)"""

    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(primary_key=True)
    fund_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="펀드 표준코드")
    fund_name: Mapped[str] = mapped_column(String(300), index=True, comment="펀드명")
    company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="SET NULL"), index=True, comment="운용사 기업 ID"
    )
    fund_type: Mapped[str] = mapped_column(String(20), comment="펀드 유형 (blind/project)")
    fund_category: Mapped[str | None] = mapped_column(String(50), comment="펀드 분류 (VC/PEF)")
    company_name: Mapped[str] = mapped_column(String(200), index=True, comment="운용사명")
    company_code: Mapped[str | None] = mapped_column(String(50), comment="운용사 코드")
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="설정액 (원)")
    management_fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="운용보수율 (%)")
    performance_fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="성과보수율 (%)")
    established_date: Mapped[date | None] = mapped_column(Date, comment="설정일")
    maturity_date: Mapped[date | None] = mapped_column(Date, comment="만기일")
    vintage_year: Mapped[int | None] = mapped_column(comment="빈티지 연도")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 상태")
    is_maturity_alert: Mapped[bool] = mapped_column(Boolean, default=False, comment="회수 집중 구간 여부 (7~10년차)")
    description: Mapped[str | None] = mapped_column(Text, comment="펀드 설명")
    source_url: Mapped[str | None] = mapped_column(String(500), comment="출처 URL")

    company: Mapped["Company | None"] = relationship(back_populates="funds")  # noqa: F821
    managers: Mapped[list["FundManager"]] = relationship(back_populates="fund", cascade="all, delete-orphan")


class FundManager(TimestampMixin, Base):
    """펀드 운용 전문인력 모델"""

    __tablename__ = "fund_managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id", ondelete="CASCADE"), index=True)
    manager_name: Mapped[str] = mapped_column(String(100), index=True, comment="운용인력 이름")
    position: Mapped[str | None] = mapped_column(String(100), comment="직책")
    role: Mapped[str | None] = mapped_column(String(100), comment="역할 (펀드매니저/심사역)")
    career_years: Mapped[int | None] = mapped_column(comment="경력 년수")
    education: Mapped[str | None] = mapped_column(String(200), comment="학력")
    certifications: Mapped[str | None] = mapped_column(Text, comment="자격증")
    appointed_date: Mapped[date | None] = mapped_column(Date, comment="임명일")
    resigned_date: Mapped[date | None] = mapped_column(Date, comment="사임일")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="재직 여부")
    specialty_sectors: Mapped[str | None] = mapped_column(Text, comment="전문 섹터 (JSON)")
    profile_summary: Mapped[str | None] = mapped_column(Text, comment="프로필 요약")
    total_deals_involved: Mapped[int] = mapped_column(default=0, comment="관여 딜 수")

    fund: Mapped["Fund"] = relationship(back_populates="managers")
