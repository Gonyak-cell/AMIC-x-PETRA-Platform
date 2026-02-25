"""평판 분석 스키마"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ReputationScoreResponse(BaseModel):
    """평판 점수 응답"""

    model_config = ConfigDict(from_attributes=True)

    company_id: int
    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="기업명")
    trend_score: Decimal = Field(..., description="트렌드 점수 (0.0~1.0)")
    news_score: Decimal = Field(..., description="뉴스 평판 점수 (-1.0~1.0)")
    performance_score: Decimal = Field(..., description="성과 지표 점수 (0.0~1.0)")
    total_score: Decimal = Field(..., description="총합 평판 지수 (0.0~1.0)")
    status_tag: str = Field(..., description="상태 태그 (rising/stable/risk)")
    scored_at: datetime = Field(..., description="점수 산출 시각")
    news_count: int = Field(0, description="분석 뉴스 수")
    exit_count: int = Field(0, description="1년 내 엑시트 횟수")

    @field_serializer("trend_score", "news_score", "performance_score", "total_score")
    @classmethod
    def _serialize_scores(cls, v: Decimal) -> float:
        return float(v)


class ReputationHistoryItem(BaseModel):
    """평판 이력 아이템"""

    model_config = ConfigDict(from_attributes=True)

    total_score: Decimal = Field(..., description="총합 평판 지수")
    status_tag: str = Field(..., description="상태 태그")
    trend_score: Decimal = Field(..., description="트렌드 점수")
    news_score: Decimal = Field(..., description="뉴스 점수")
    performance_score: Decimal = Field(..., description="성과 점수")
    recorded_at: datetime = Field(..., description="기록 시각")

    @field_serializer("total_score", "trend_score", "news_score", "performance_score")
    @classmethod
    def _serialize_scores(cls, v: Decimal) -> float:
        return float(v)


class ReputationHistoryResponse(BaseModel):
    """평판 이력 응답"""

    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="기업명")
    total: int = Field(..., description="이력 건수")
    items: list[ReputationHistoryItem] = Field(default_factory=list, description="이력 목록")


class ReputationCalculateRequest(BaseModel):
    """평판 계산 요청"""

    months: int = Field(6, ge=1, le=24, description="뉴스 분석 기간 (개월)")
    save_history: bool = Field(True, description="이력 저장 여부")


class ReputationListItem(BaseModel):
    """평판 목록 아이템"""

    model_config = ConfigDict(from_attributes=True)

    company_id: int
    corp_code: str
    corp_name: str
    total_score: Decimal
    status_tag: str
    scored_at: datetime | None

    @field_serializer("total_score")
    @classmethod
    def _serialize_scores(cls, v: Decimal) -> float:
        return float(v)


class ReputationListResponse(BaseModel):
    """평판 목록 응답"""

    total: int = Field(..., description="총 건수")
    page: int = Field(..., description="페이지 번호")
    size: int = Field(..., description="페이지 크기")
    items: list[ReputationListItem] = Field(default_factory=list, description="평판 목록")


class ReputationThemeItem(BaseModel):
    """테마별 뉴스 분포 아이템"""

    theme_code: str = Field(..., description="테마 코드 (exit_ipo, mna, financial_risk 등)")
    display_name: str = Field(..., description="테마 표시명")
    sentiment: str = Field(..., description="감성 방향 (positive / negative)")
    count: int = Field(0, description="해당 테마 뉴스 건수")


class ReputationThemeResponse(BaseModel):
    """테마별 평판 분석 응답"""

    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="기업명")
    period_months: int = Field(..., description="분석 기간 (개월)")
    themes: list[ReputationThemeItem] = Field(default_factory=list, description="테마별 뉴스 건수 목록")
    risk_absence_notices: list[str] = Field(default_factory=list, description="리스크 부재 알림 문구")
    total_articles: int = Field(0, description="분석 대상 총 기사 수")
