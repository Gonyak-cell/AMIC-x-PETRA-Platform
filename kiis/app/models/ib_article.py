"""IB 매체 기사 모델

IB 전문 매체(인베스트조선, 딜사이트, IB토마토, 블로터)에서 수집한
무료 공개 기사의 메타데이터 및 NLP 분류 결과를 저장한다.

저작권 보호 원칙:
- 기사 전문(content) 저장 금지
- lead_text(첫 문단)만 저장
- canonical_url(원문 링크) 필수 병기
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class IBCategory(StrEnum):
    """IB 기사 추출 카테고리 (5종)"""

    DEAL_PROGRESS = "deal_progress"
    SOURCING_HISTORY = "sourcing_history"
    INVESTMENT_STYLE = "investment_style"
    REPUTATION = "reputation"
    PERSONNEL_EVALUATION = "personnel_evaluation"


class IBDomain(StrEnum):
    """도메인 분류 (Fact vs Opinion)"""

    FACT = "fact"
    OPINION = "opinion"


# 카테고리 → 도메인 매핑
CATEGORY_DOMAIN_MAP: dict[str, str] = {
    IBCategory.DEAL_PROGRESS: IBDomain.FACT,
    IBCategory.SOURCING_HISTORY: IBDomain.FACT,
    IBCategory.INVESTMENT_STYLE: IBDomain.OPINION,
    IBCategory.REPUTATION: IBDomain.OPINION,
    IBCategory.PERSONNEL_EVALUATION: IBDomain.OPINION,
}

# 카테고리 → 한글 표시명
CATEGORY_DISPLAY_MAP: dict[str, str] = {
    IBCategory.DEAL_PROGRESS: "딜 진행",
    IBCategory.SOURCING_HISTORY: "소싱 내역",
    IBCategory.INVESTMENT_STYLE: "투자 성향",
    IBCategory.REPUTATION: "GP 평판",
    IBCategory.PERSONNEL_EVALUATION: "운용인력 평가",
}

# 수집 대상 매체 목록
IB_SOURCES: list[str] = ["investchosun", "dealsite", "ibtomato", "bloter"]


def get_category_display(category: str | None) -> str:
    """카테고리의 한글 표시명을 반환한다."""
    if not category:
        return "미분류"
    return CATEGORY_DISPLAY_MAP.get(category, "미분류")


# 크롤링 상수
MAX_LEAD_TEXT_LENGTH: int = 1000
MIN_PARAGRAPH_LENGTH: int = 30
MAX_GP_MATCH_TOKENS: int = 10

# Redis Lock 상수 (라우터 + 스케줄러 태스크 공유)
IB_CRAWL_LOCK_KEY: str = "ib:crawl:lock"
IB_CRAWL_LOCK_TTL: int = 600  # 10분


class IBArticle(TimestampMixin, Base):
    """IB 매체 기사 모델

    무료 공개 기사의 메타데이터 + NLP 분류 결과 + GP 매칭 결과를 저장한다.
    기사 전문은 저장하지 않으며, lead_text(첫 문단)와 canonical_url만 기록한다.
    """

    __tablename__ = "ib_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True, comment="기사 제목")
    lead_text: Mapped[str | None] = mapped_column(Text, comment="첫 문단 (저작권 보호, 전문 저장 금지)")
    source: Mapped[str] = mapped_column(
        String(50), index=True, comment="출처 (investchosun, dealsite, ibtomato, bloter)"
    )
    author: Mapped[str | None] = mapped_column(String(100), comment="저자")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment="발행일시")
    canonical_url: Mapped[str] = mapped_column(String(1000), unique=True, comment="원문 아웃링크 (필수)")
    url_hash: Mapped[str] = mapped_column(String(64), index=True, comment="URL SHA256 해시 (중복 감지)")
    is_paywalled: Mapped[bool] = mapped_column(Boolean, default=False, comment="Paywall 감지 여부")

    # NLP 분류 결과
    category: Mapped[str | None] = mapped_column(
        String(30),
        index=True,
        comment="카테고리 (deal_progress, sourcing_history, investment_style, reputation, personnel_evaluation)",
    )
    domain: Mapped[str | None] = mapped_column(String(10), comment="도메인 (fact, opinion)")
    sentiment_score: Mapped[float | None] = mapped_column(Float, comment="감성 점수 (-1.0 ~ 1.0)")
    keywords: Mapped[str | None] = mapped_column(Text, comment="키워드 (JSON 문자열)")

    # GP 매칭
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True, comment="매칭된 GP 기업 ID"
    )
    match_confidence: Mapped[float | None] = mapped_column(Float, comment="GP 매칭 신뢰도 (0.0 ~ 1.0)")

    company: Mapped["Company | None"] = relationship(back_populates="ib_articles")  # noqa: F821

    # 3섹션 멀티라벨 분류 (ma / governance / fund)
    section_primary: Mapped[str | None] = mapped_column(
        String(20), index=True, comment="대표 섹션 (ma, governance, fund)"
    )
    section_labels_json: Mapped[str | None] = mapped_column(Text, comment='통과 라벨 JSON (예: ["ma", "governance"])')
    section_scores_json: Mapped[str | None] = mapped_column(Text, comment="섹션별 점수 + 근거 JSON")
    section_classified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="섹션 분류 실행 시각"
    )
    section_version: Mapped[str | None] = mapped_column(
        String(20), comment="분류 규칙 버전 (ma_section_rules.json version)"
    )
