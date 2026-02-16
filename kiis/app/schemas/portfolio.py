"""포트폴리오 생존분석 스키마"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PortfolioCompanyItem(BaseModel):
    """포트폴리오 기업 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    investor_company_id: int = Field(..., description="투자사 ID")
    target_company_name: str = Field(..., description="피투자사명")
    target_company_id: int | None = Field(None, description="피투자사 ID")
    deal_id: int | None = Field(None, description="관련 딜 ID")
    survival_status: str = Field(..., description="생존 상태")
    last_audit_date: date | None = Field(None, description="최근 감사보고서 접수일")
    last_audit_rcept_no: str | None = Field(None, description="최근 감사보고서 접수번호")
    dissolution_date: date | None = Field(None, description="해산/폐업 공시일")
    dissolution_rcept_no: str | None = Field(None, description="해산/폐업 공시 접수번호")
    estimated_valuation: Decimal | None = Field(None, description="추정 기업가치 (원)")
    is_unicorn: bool = Field(False, description="유니콘 여부")
    checked_at: datetime | None = Field(None, description="마지막 생존 확인 시각")
    notes: str | None = Field(None, description="비고")


class PortfolioListItem(BaseModel):
    """포트폴리오 목록 아이템 (간략)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_company_name: str
    survival_status: str
    is_unicorn: bool
    deal_date: date | None = Field(None, description="거래일")


class PortfolioListResponse(BaseModel):
    """포트폴리오 목록 응답 (페이지네이션)"""

    total: int = Field(..., description="총 건수")
    page: int = Field(..., description="페이지 번호")
    size: int = Field(..., description="페이지 크기")
    items: list[PortfolioCompanyItem] = Field(default_factory=list, description="포트폴리오 목록")


class PortfolioSummaryResponse(BaseModel):
    """포트폴리오 요약 (생존 상태별 집계)"""

    total: int = Field(..., description="총 포트폴리오 수")
    active_count: int = Field(0, description="정상 영업 수")
    audit_missing_count: int = Field(0, description="감사보고서 미제출 수")
    dissolved_count: int = Field(0, description="해산/폐업 수")
    unicorn_count: int = Field(0, description="유니콘 수")
    unknown_count: int = Field(0, description="미확인 수")


class SurvivalCheckResponse(BaseModel):
    """생존 확인 결과"""

    portfolio_id: int = Field(..., description="포트폴리오 ID")
    previous_status: str = Field(..., description="이전 생존 상태")
    new_status: str = Field(..., description="새 생존 상태")
    checked_at: datetime = Field(..., description="확인 시각")


class ValuationUpdateRequest(BaseModel):
    """기업가치 업데이트 요청"""

    estimated_valuation: Decimal = Field(..., description="추정 기업가치 (원)", gt=0)


class ValuationUpdateResponse(BaseModel):
    """기업가치 업데이트 응답"""

    portfolio_id: int = Field(..., description="포트폴리오 ID")
    target_company_name: str = Field(..., description="피투자사명")
    estimated_valuation: Decimal = Field(..., description="추정 기업가치 (원)")
    is_unicorn: bool = Field(..., description="유니콘 여부")
    is_newly_unicorn: bool = Field(..., description="이번에 유니콘이 되었는지 여부")
    survival_status: str = Field(..., description="생존 상태")
