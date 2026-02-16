from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class REITs(TimestampMixin, Base):
    """리츠 모델"""

    __tablename__ = "reits"

    id: Mapped[int] = mapped_column(primary_key=True)
    reits_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="리츠 코드")
    company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="SET NULL"), index=True, comment="관리 기업 ID"
    )
    reits_name: Mapped[str] = mapped_column(String(300), index=True, comment="리츠명")
    reits_type: Mapped[str] = mapped_column(String(20), comment="리츠 유형 (self_managed/entrusted)")
    management_company: Mapped[str | None] = mapped_column(String(200), comment="자산관리회사명")
    establishment_date: Mapped[date | None] = mapped_column(Date, comment="설립인가일")
    listing_date: Mapped[date | None] = mapped_column(Date, comment="상장일")
    total_assets: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="총자산 (백만원)")
    real_estate_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="부동산 자산액 (백만원)")
    real_estate_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="부동산 비율 (%)")
    has_asset_ratio_warning: Mapped[bool] = mapped_column(Boolean, default=False, comment="부동산 70% 미달 경고")
    dividend_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="배당수익률 (%)")
    dividend_payout_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), comment="배당성향 (배당금/당기순이익, %)"
    )
    net_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="당기순이익 (백만원)")
    total_dividend: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="배당금 총액 (백만원)")
    employee_count: Mapped[int | None] = mapped_column(comment="임직원 수")
    status: Mapped[str] = mapped_column(
        String(20), default="authorized", comment="상태 (authorized/operating/dissolved)"
    )
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False, comment="상장 여부")
    description: Mapped[str | None] = mapped_column(Text, comment="리츠 설명")
    source_url: Mapped[str | None] = mapped_column(String(500), comment="출처 URL")

    company: Mapped["Company | None"] = relationship(back_populates="reits_list")  # noqa: F821
    assets: Mapped[list["REITsAsset"]] = relationship(back_populates="reits", cascade="all, delete-orphan")


class REITsAsset(TimestampMixin, Base):
    """리츠 보유 자산 모델"""

    __tablename__ = "reits_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    reits_id: Mapped[int] = mapped_column(ForeignKey("reits.id", ondelete="CASCADE"), index=True)
    asset_name: Mapped[str] = mapped_column(String(300), comment="자산명")
    asset_type: Mapped[str] = mapped_column(
        String(50), comment="자산 유형 (office/logistics/residential/retail/hotel/other)"
    )
    asset_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="자산 가액 (백만원)")
    asset_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="자산 비율 (%)")
    location: Mapped[str | None] = mapped_column(String(300), comment="소재지")
    acquisition_date: Mapped[date | None] = mapped_column(Date, comment="취득일")

    reits: Mapped["REITs"] = relationship(back_populates="assets")
