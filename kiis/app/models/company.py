from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Company(TimestampMixin, Base):
    """통합 기업 모델 (DART 기업 개황 + GP 프로파일)"""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    corp_code: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True, nullable=True, comment="DART 고유번호 (비공시 GP는 NULL)"
    )
    corp_name: Mapped[str] = mapped_column(String(300), index=True, comment="정식명칭")
    corp_name_eng: Mapped[str | None] = mapped_column(String(300), comment="영문명칭")
    stock_name: Mapped[str | None] = mapped_column(String(100), comment="종목명")
    stock_code: Mapped[str | None] = mapped_column(String(20), index=True, comment="종목코드")
    ceo_nm: Mapped[str | None] = mapped_column(String(100), comment="대표자명")
    corp_cls: Mapped[str | None] = mapped_column(String(5), comment="법인구분 (Y:유가, K:코스닥, N:코넥스, E:기타)")
    jurir_no: Mapped[str | None] = mapped_column(String(20), unique=True, comment="법인등록번호")
    bizr_no: Mapped[str | None] = mapped_column(String(20), comment="사업자등록번호")
    adres: Mapped[str | None] = mapped_column(Text, comment="주소")
    hm_url: Mapped[str | None] = mapped_column(String(500), comment="홈페이지")
    ir_url: Mapped[str | None] = mapped_column(String(500), comment="IR 홈페이지")
    logo_url: Mapped[str | None] = mapped_column(String(1000), comment="로고 이미지 URL")
    logo_source: Mapped[str | None] = mapped_column(String(30), comment="로고 소스 (og_image/meta_icon/favicon)")
    logo_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="로고 수집 시각")
    phn_no: Mapped[str | None] = mapped_column(String(50), comment="전화번호")
    fax_no: Mapped[str | None] = mapped_column(String(50), comment="팩스번호")
    induty_code: Mapped[str | None] = mapped_column(String(20), comment="업종코드")
    est_dt: Mapped[str | None] = mapped_column(String(10), comment="설립일 (YYYYMMDD)")
    acc_mt: Mapped[str | None] = mapped_column(String(5), comment="결산월")

    # GP 프로파일 (사모펀드 운용사 전용 — nullable)
    is_gp: Mapped[bool] = mapped_column(Boolean, default=False, index=True, comment="GP(사모펀드 운용사) 여부")
    finance_company_code: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, comment="금융회사코드 (공공데이터포털)"
    )
    gp_authorization_date: Mapped[str | None] = mapped_column(String(10), comment="인가일자")
    gp_aum: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="운용자산 AUM (백만원)")
    gp_fund_count: Mapped[int | None] = mapped_column(comment="운용 펀드수")
    gp_employee_count: Mapped[int | None] = mapped_column(comment="임직원수")
    gp_strategy_tags: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, comment="전략 태그"
    )
    gp_total_commitment: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 0), nullable=True, comment="FSS PEF 총약정액 합산 (억원, GP1+GP2+GP3 참여분)"
    )
    gp_profile_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="GP 프로파일 마지막 동기화 시각"
    )

    funds: Mapped[list["Fund"]] = relationship(back_populates="company")  # noqa: F821
    reits_list: Mapped[list["REITs"]] = relationship(back_populates="company")  # noqa: F821
    news_articles: Mapped[list["NewsArticle"]] = relationship(back_populates="company")  # noqa: F821
    aliases: Mapped[list["CompanyAlias"]] = relationship(back_populates="company", cascade="all, delete-orphan")

    # 평판 점수 (1:1 관계)
    reputation_score: Mapped["ReputationScore | None"] = relationship(  # noqa: F821
        back_populates="company", uselist=False
    )
    # 투자사로서의 딜 목록
    deals_as_investor: Mapped[list["Deal"]] = relationship(  # noqa: F821
        foreign_keys="Deal.company_id", back_populates="investor_company"
    )
    # 피투자사로서의 딜 목록
    deals_as_target: Mapped[list["Deal"]] = relationship(  # noqa: F821
        foreign_keys="Deal.target_company_id", back_populates="target"
    )
    # IB 매체 기사
    ib_articles: Mapped[list["IBArticle"]] = relationship(back_populates="company")  # noqa: F821
    # GP가 운용하는 KVIC 자조합 목록
    kvic_funds: Mapped[list["KVICFund"]] = relationship(  # noqa: F821
        back_populates="company", cascade="all, delete-orphan"
    )
    # GP1으로 참여하는 PEF 목록
    pef_funds_as_gp1: Mapped[list["PEFFund"]] = relationship(  # noqa: F821
        foreign_keys="PEFFund.gp1_company_id", back_populates="gp1_company"
    )


class CompanyAlias(TimestampMixin, Base):
    """기업 별칭 사전 모델

    동일 법인의 다양한 표기를 정규 corp_code에 매핑한다.
    예: "한투파" → company.corp_code("한국투자파트너스 주식회사")
    """

    __tablename__ = "company_aliases"
    __table_args__ = (UniqueConstraint("alias_name", "company_id", name="uq_alias_company"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alias_name: Mapped[str] = mapped_column(String(300), index=True, comment="별칭 (약칭, 줄임말 등)")
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, comment="정규 기업 ID"
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, default=True, comment="수동 등록 여부 (False=자동 생성)")

    company: Mapped["Company"] = relationship(back_populates="aliases")
