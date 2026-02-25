"""딜 소싱 스키마"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DealItem(BaseModel):
    """딜 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = Field(None, description="투자사 ID")
    investor_name: str | None = Field(None, description="투자사명")
    target_company: str = Field(..., description="피투자사명")
    target_company_id: int | None = Field(None, description="피투자사 ID")
    amount: Decimal | None = Field(None, description="투자 금액 (원)")
    amount_display: str | None = Field(None, description="투자 금액 표시용")
    round_stage: str | None = Field(None, description="투자 단계")
    sector: str | None = Field(None, description="투자 섹터")
    deal_date: date | None = Field(None, description="거래일")
    deal_year: int | None = Field(None, description="거래 연도")
    source_url: str | None = Field(None, description="출처 URL")
    source_type: str | None = Field(None, description="출처 유형")
    is_lead_investor: bool = Field(False, description="리드 투자사 여부")
    fund_id: int | None = Field(None, description="펀드 ID")
    fund_code: str | None = Field(None, description="펀드 코드")
    fund_name: str | None = Field(None, description="펀드명")


class DealListItem(BaseModel):
    """딜 목록 아이템 (간략)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_company: str
    amount_display: str | None
    round_stage: str | None
    sector: str | None
    deal_date: date | None


class DealListResponse(BaseModel):
    """딜 목록 응답"""

    total: int = Field(..., description="총 건수")
    page: int = Field(..., description="페이지 번호")
    size: int = Field(..., description="페이지 크기")
    items: list[DealItem] = Field(default_factory=list, description="딜 목록")


class SectorAggregation(BaseModel):
    """섹터별 집계"""

    sector: str = Field(..., description="섹터 코드")
    sector_name: str = Field(..., description="섹터 표시명")
    deal_count: int = Field(..., description="딜 수")
    total_amount: Decimal | None = Field(None, description="총 투자 금액 (원)")


class SectorAggregationResponse(BaseModel):
    """섹터별 집계 응답"""

    total_deals: int = Field(..., description="총 딜 수")
    items: list[SectorAggregation] = Field(default_factory=list, description="섹터별 집계")


class StageAggregation(BaseModel):
    """단계별 집계"""

    stage: str = Field(..., description="투자 단계 코드")
    stage_name: str = Field(..., description="단계 표시명")
    deal_count: int = Field(..., description="딜 수")
    total_amount: Decimal | None = Field(None, description="총 투자 금액 (원)")


class StageAggregationResponse(BaseModel):
    """단계별 집계 응답"""

    total_deals: int = Field(..., description="총 딜 수")
    items: list[StageAggregation] = Field(default_factory=list, description="단계별 집계")


class YearlyTrend(BaseModel):
    """연도별 트렌드"""

    year: int = Field(..., description="연도")
    deal_count: int = Field(..., description="딜 수")
    total_amount: Decimal | None = Field(None, description="총 투자 금액 (원)")


class TrendResponse(BaseModel):
    """트렌드 응답"""

    corp_code: str | None = Field(None, description="투자사 DART 고유번호")
    corp_name: str | None = Field(None, description="투자사명")
    items: list[YearlyTrend] = Field(default_factory=list, description="연도별 트렌드")


class AmountBucket(BaseModel):
    """투자 금액 구간별 분포"""

    bucket_label: str = Field(..., description="구간 라벨 (예: '10억 미만')")
    bucket_min: int = Field(..., description="구간 하한 (억원)")
    bucket_max: int | None = Field(None, description="구간 상한 (억원)")
    deal_count: int = Field(..., description="해당 구간 딜 수")
    total_amount: Decimal | None = Field(None, description="해당 구간 합계 (원)")


class DealAmountStats(BaseModel):
    """투자 규모 통계"""

    total_deals: int = Field(..., description="총 딜 수")
    total_amount: Decimal | None = Field(None, description="총 투자 금액 (원)")
    avg_amount: Decimal | None = Field(None, description="평균 투자 금액 (원)")
    median_amount: Decimal | None = Field(None, description="중앙값 (원)")
    min_amount: Decimal | None = Field(None, description="최소 투자 금액 (원)")
    max_amount: Decimal | None = Field(None, description="최대 투자 금액 (원)")
    distribution: list[AmountBucket] = Field(
        default_factory=list, description="금액 구간별 분포"
    )


class DealCreateRequest(BaseModel):
    """딜 생성 요청"""

    target_company: str = Field(..., min_length=1, description="피투자사명")
    amount: Decimal | None = Field(None, description="투자 금액 (원)")
    amount_display: str | None = Field(None, description="투자 금액 표시용")
    round_stage: str | None = Field(None, description="투자 단계")
    sector: str | None = Field(None, description="투자 섹터")
    deal_date: date | None = Field(None, description="거래일")
    source_url: str | None = Field(None, description="출처 URL")
    source_type: str | None = Field(None, description="출처 유형")
    is_lead_investor: bool = Field(False, description="리드 투자사 여부")
    description: str | None = Field(None, description="딜 설명")


class TendencyDealItem(BaseModel):
    """투자성향 - 대표 딜 아이템"""

    target_company: str
    amount_display: str | None = None
    round_stage: str | None = None
    deal_date: date | None = None
    source_url: str | None = None


class TendencySectorDetail(BaseModel):
    """투자성향 - 섹터별 상세"""

    sector: str
    sector_name: str
    deal_count: int
    total_amount: Decimal | None = None
    total_amount_display: str | None = None
    percentage: float
    description: str
    deals: list[TendencyDealItem] = Field(default_factory=list)


class TendencyStageDetail(BaseModel):
    """투자성향 - 스테이지별 상세"""

    stage: str
    stage_name: str
    deal_count: int
    total_amount: Decimal | None = None
    total_amount_display: str | None = None
    percentage: float
    description: str
    deals: list[TendencyDealItem] = Field(default_factory=list)


class TendencySummaryResponse(BaseModel):
    """투자성향 정성적 요약 응답"""

    corp_code: str
    years: int
    total_deals: int
    total_amount: Decimal | None = None
    total_amount_display: str | None = None
    summary_text: str
    sector_summary: str
    stage_summary: str
    sectors: list[TendencySectorDetail] = Field(default_factory=list)
    stages: list[TendencyStageDetail] = Field(default_factory=list)


class DealExtractRequest(BaseModel):
    """뉴스에서 딜 추출 요청"""

    news_article_id: int = Field(..., description="뉴스 기사 ID")
    investor_corp_code: str | None = Field(None, description="투자사 DART 고유번호 (선택)")
    fund_code: str | None = Field(None, description="펀드 코드 (펀드 단위 딜 추적)")
