from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NewsItem(BaseModel):
    """뉴스 기사 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str = Field(..., description="기사 제목")
    content: str | None = Field(None, description="기사 본문")
    summary: str | None = Field(None, description="기사 요약")
    source: str = Field(..., description="출처 (platum, dealsite 등)")
    author: str | None = Field(None, description="저자")
    published_at: datetime | None = Field(None, description="발행일시")
    url: str = Field(..., description="기사 URL")
    sentiment_score: float | None = Field(None, description="감성 점수 (-1.0 ~ 1.0)")
    keywords: str | None = Field(None, description="키워드 (JSON)")
    company_id: int | None = Field(None, description="관련 기업 ID")


class NewsListItem(BaseModel):
    """뉴스 목록 아이템 (간략 정보)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str = Field(..., description="기사 제목")
    source: str = Field(..., description="출처")
    author: str | None = Field(None, description="저자")
    published_at: datetime | None = Field(None, description="발행일시")
    url: str = Field(..., description="기사 URL")
    sentiment_score: float | None = Field(None, description="감성 점수")


class NewsListResponse(BaseModel):
    """뉴스 목록 응답"""

    total: int
    page: int
    size: int
    items: list[NewsListItem]


class NewsCollectResponse(BaseModel):
    """뉴스 수집 결과 응답"""

    source: str = Field(..., description="수집 소스")
    collected: int = Field(..., description="수집된 기사 수")
    duplicates: int = Field(..., description="중복 기사 수")
    new_articles: int = Field(..., description="신규 저장 기사 수")
