"""IB 인사이트 Pydantic 스키마

API 요청/응답 모델. Fact/Opinion 도메인을 엄격히 분리한다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IBArticleItem(BaseModel):
    """IB 기사 아이템 (공통 필드)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    lead_text: str | None = None
    canonical_url: str
    source: str
    published_at: datetime | None = None

    # 3섹션 분류 (뉴스피드 소비자용)
    category: str | None = None  # section_primary 매핑
    category_display: str = "미분류"
    labels: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)

    # 레거시 IB 인사이트 분류
    insight_category: str | None = None
    insight_domain: str | None = None

    sentiment_score: float | None = None
    is_paywalled: bool = False


class IBFactItem(IBArticleItem):
    """Fact 도메인 아이템 (deal_progress, sourcing_history)"""

    pass


class IBOpinionItem(IBArticleItem):
    """Opinion 도메인 아이템 (investment_style, reputation, personnel_evaluation)"""

    pass


class IBInsightResponse(BaseModel):
    """GP별 IB 인사이트 응답 (Fact/Opinion 엄격 분리)"""

    corp_code: str
    corp_name: str
    total_articles: int
    facts: list[IBFactItem]
    opinions: list[IBOpinionItem]
    last_collected_at: datetime | None = None
    disclaimer: str = Field(
        default=(
            "본 내용은 인베스트조선, 딜사이트, IB토마토, 블로터 등 IB 매체의 무료 공개 기사에서 "
            "추출한 주관적 평가 및 의견으로, 당사의 공식 입장이 아닙니다."
        ),
        description="Opinion 섹션 면책 조항",
    )


class IBArticleListResponse(BaseModel):
    """IB 기사 목록 응답"""

    items: list[IBArticleItem]
    total: int
    page: int
    size: int


class IBCollectSourceResult(BaseModel):
    """매체별 수집 결과"""

    collected: int = 0
    new: int = 0
    duplicates: int = 0


class IBCollectResponse(BaseModel):
    """IB 수집 결과 응답"""

    results: dict[str, IBCollectSourceResult]
    classified: int
