"""딜(투자 거래) 모델

투자사의 딜 소싱 데이터를 저장하고 섹터/단계별 분석을 지원한다.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DealSector(StrEnum):
    """투자 섹터"""

    AI_DEEPTECH = "ai_deeptech"  # AI/딥테크
    BIO_HEALTH = "bio_health"  # 바이오/헬스케어
    SAAS = "saas"  # SaaS
    CONSUMER = "consumer"  # 컨슈머
    FINTECH = "fintech"  # 핀테크
    MOBILITY = "mobility"  # 모빌리티
    ECOMMERCE = "ecommerce"  # 이커머스
    CONTENT = "content"  # 콘텐츠/미디어
    PROPTECH = "proptech"  # 프롭테크
    EDTECH = "edtech"  # 에드테크
    OTHER = "other"  # 기타


class DealStage(StrEnum):
    """투자 단계"""

    SEED = "seed"  # 시드
    PRE_A = "pre_a"  # 프리A
    SERIES_A = "series_a"  # 시리즈A
    SERIES_B = "series_b"  # 시리즈B
    SERIES_C = "series_c"  # 시리즈C 이상
    PRE_IPO = "pre_ipo"  # Pre-IPO
    BRIDGE = "bridge"  # 브릿지


# 섹터 표시명 매핑
SECTOR_DISPLAY_NAMES = {
    DealSector.AI_DEEPTECH: "AI/딥테크",
    DealSector.BIO_HEALTH: "바이오/헬스케어",
    DealSector.SAAS: "SaaS",
    DealSector.CONSUMER: "컨슈머",
    DealSector.FINTECH: "핀테크",
    DealSector.MOBILITY: "모빌리티",
    DealSector.ECOMMERCE: "이커머스",
    DealSector.CONTENT: "콘텐츠/미디어",
    DealSector.PROPTECH: "프롭테크",
    DealSector.EDTECH: "에드테크",
    DealSector.OTHER: "기타",
}

# 단계 표시명 매핑
STAGE_DISPLAY_NAMES = {
    DealStage.SEED: "시드",
    DealStage.PRE_A: "프리A",
    DealStage.SERIES_A: "시리즈A",
    DealStage.SERIES_B: "시리즈B",
    DealStage.SERIES_C: "시리즈C+",
    DealStage.PRE_IPO: "Pre-IPO",
    DealStage.BRIDGE: "브릿지",
}


class Deal(TimestampMixin, Base):
    """딜(투자 거래) 모델"""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 투자사 정보
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="투자사(GP) 기업 ID",
    )

    # 펀드 정보 (펀드 단위 딜 추적)
    fund_id: Mapped[int | None] = mapped_column(
        ForeignKey("funds.id", ondelete="SET NULL"),
        index=True,
        comment="펀드 ID (펀드 단위 딜 추적)",
    )

    # 피투자사 정보
    target_company: Mapped[str] = mapped_column(String(300), index=True, comment="피투자사명")
    target_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="피투자사 기업 ID (식별된 경우)",
    )

    # 투자 금액
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), comment="투자 금액 (원)")
    amount_display: Mapped[str | None] = mapped_column(String(50), comment="투자 금액 표시용 (예: 100억원)")

    # 투자 분류
    round_stage: Mapped[str | None] = mapped_column(String(30), index=True, comment="투자 단계 (seed/series_a/...)")
    sector: Mapped[str | None] = mapped_column(String(30), index=True, comment="투자 섹터 (ai_deeptech/bio_health/...)")
    sector_keywords: Mapped[str | None] = mapped_column(Text, comment="섹터 분류 근거 키워드 (JSON)")

    # 날짜
    deal_date: Mapped[date | None] = mapped_column(Date, index=True, comment="거래일")
    deal_year: Mapped[int | None] = mapped_column(index=True, comment="거래 연도 (집계용)")

    # 출처
    source_url: Mapped[str | None] = mapped_column(String(1000), comment="출처 URL")
    source_type: Mapped[str | None] = mapped_column(String(50), comment="출처 유형 (news/disclosure/manual)")
    news_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("news_articles.id", ondelete="SET NULL"),
        comment="원본 뉴스 ID",
    )

    # 추가 정보
    is_lead_investor: Mapped[bool] = mapped_column(Boolean, default=False, comment="리드 투자사 여부")
    co_investors: Mapped[str | None] = mapped_column(Text, comment="공동 투자사 목록 (JSON)")
    description: Mapped[str | None] = mapped_column(Text, comment="딜 설명")

    # 관계
    investor_company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[company_id]
    )
    target: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[target_company_id]
    )
    news_article: Mapped["NewsArticle | None"] = relationship()  # noqa: F821
    fund: Mapped["Fund | None"] = relationship(  # noqa: F821
        foreign_keys=[fund_id], back_populates="deals"
    )
