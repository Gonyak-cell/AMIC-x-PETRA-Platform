"""통합 검색 Pydantic 스키마"""

from pydantic import BaseModel, ConfigDict, Field


class SearchQuery(BaseModel):
    """통합 검색 요청 파라미터"""

    model_config = ConfigDict(from_attributes=True)

    q: str = Field(..., min_length=1, max_length=200, description="검색어")
    type: str | None = Field(
        None,
        description="검색 대상 (companies/funds/news/deals). None이면 전체 검색",
    )
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(20, ge=1, le=100, description="페이지당 결과 수")


class SearchResultItem(BaseModel):
    """검색 결과 개별 항목"""

    model_config = ConfigDict(from_attributes=True)

    index: str = Field(description="인덱스명 (kiis_companies, kiis_funds 등)")
    id: str = Field(description="문서 ID")
    score: float = Field(description="검색 관련도 점수")
    source: dict = Field(description="ES document 원본 데이터")


class SearchResponse(BaseModel):
    """통합 검색 응답"""

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(description="총 검색 결과 수")
    page: int = Field(description="현재 페이지")
    size: int = Field(description="페이지당 결과 수")
    query: str = Field(description="검색어")
    items: list[SearchResultItem] = Field(description="검색 결과 목록")


class ReindexResponse(BaseModel):
    """리인덱싱 응답"""

    model_config = ConfigDict(from_attributes=True)

    companies: int = Field(description="인덱싱된 기업 수")
    funds: int = Field(description="인덱싱된 펀드 수")
    news: int = Field(description="인덱싱된 뉴스 수")
    deals: int = Field(description="인덱싱된 딜 수")
    message: str = "리인덱싱 완료"


class IndexStatusResponse(BaseModel):
    """인덱스 상태 응답"""

    model_config = ConfigDict(from_attributes=True)

    indices: dict[str, dict] = Field(description="인덱스별 문서 수, 크기 등")
