from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


# --- GP 정보 (Co-GP) ---
class GPInfo(BaseModel):
    """펀드의 GP 정보 (Co-GP 지원)"""

    gp_name: str = Field(..., description="GP명")
    gp_role: str = Field("gp1", description="GP 역할 (gp1/gp2/gp3)")


# --- 펀드 매니저 ---
class FundManagerItem(BaseModel):
    """펀드 운용 전문인력 정보"""

    manager_name: str = Field(..., description="운용인력 이름")
    position: str = Field("", description="직책")
    role: str = Field("", description="역할 (펀드매니저/심사역)")
    career_years: int | None = Field(None, description="경력 년수")
    education: str = Field("", description="학력")
    certifications: str = Field("", description="자격증")
    appointed_date: date | None = Field(None, description="임명일")
    resigned_date: date | None = Field(None, description="사임일")
    is_active: bool = Field(True, description="재직 여부")


class FundManagerListResponse(BaseModel):
    """운용 전문인력 목록 응답"""

    total: int
    items: list[FundManagerItem]


# --- 펀드 ---
class FundItem(BaseModel):
    """펀드 상세 정보"""

    fund_code: str = Field(..., description="펀드 표준코드")
    fund_name: str = Field(..., description="펀드명")
    fund_type: str = Field(..., description="펀드 유형 (blind/project)")
    fund_category: str = Field("", description="펀드 분류 (VC/PEF)")
    company_name: str = Field(..., description="운용사명")
    company_code: str = Field("", description="운용사 코드")
    total_amount: Decimal | None = Field(None, description="설정액 (원)")
    management_fee_rate: Decimal | None = Field(None, description="운용보수율 (%)")
    performance_fee_rate: Decimal | None = Field(None, description="성과보수율 (%)")
    established_date: date | None = Field(None, description="설정일")
    maturity_date: date | None = Field(None, description="만기일")
    vintage_year: int | None = Field(None, description="빈티지 연도")
    is_active: bool = Field(True, description="활성 상태")
    is_maturity_alert: bool = Field(False, description="회수 집중 구간 여부 (7~10년차)")
    description: str = Field("", description="펀드 설명")
    source_url: str = Field("", description="출처 URL")
    data_source: str = Field("kofia", description="데이터 소스 (kofia/pef_registry)")
    legal_basis: str | None = Field(None, description="설립근거법률")
    is_co_gp: bool = Field(False, description="Co-GP 여부")
    gp_list: list[GPInfo] | None = Field(None, description="GP 목록 (Co-GP)")
    reference_date: str | None = Field(None, description="데이터 기준시점")


class FundListItem(BaseModel):
    """펀드 목록 아이템 (간략 정보)"""

    fund_code: str = Field(..., description="펀드 표준코드")
    fund_name: str = Field(..., description="펀드명")
    fund_type: str = Field(..., description="펀드 유형 (blind/project)")
    legal_type: str = Field("", description="법률 유형 (professional_private/general_private/public)")
    asset_class: str = Field("", description="자산 클래스 (vc/pef/real_estate/infra/mezzanine/fund_of_funds)")
    fund_status: str = Field("active", description="펀드 상태 (active/harvest/liquidated)")
    company_name: str = Field(..., description="운용사명")
    total_amount: Decimal | None = Field(None, description="설정액 (원)")
    vintage_year: int | None = Field(None, description="빈티지 연도")
    is_maturity_alert: bool = Field(False, description="회수 집중 구간 여부")
    data_source: str = Field("kofia", description="데이터 소스 (kofia/pef_registry)")
    legal_basis: str | None = Field(None, description="설립근거법률")
    is_co_gp: bool = Field(False, description="Co-GP 여부")
    gp_list: list[GPInfo] | None = Field(None, description="GP 목록 (Co-GP)")
    reference_date: str | None = Field(None, description="데이터 기준시점")


class FundListResponse(BaseModel):
    """펀드 목록 응답"""

    total: int
    page: int
    size: int
    items: list[FundListItem]
    reference_date: str | None = Field(None, description="데이터 기준시점")


class FundDetailResponse(BaseModel):
    """펀드 상세 응답 (운용인력 포함)"""

    fund: FundItem
    managers: list[FundManagerItem] = Field(default_factory=list, description="운용 전문인력 목록")
    reference_date: str | None = Field(None, description="데이터 기준시점")


# --- GP(운용사) 집계 ---
class GPListItem(BaseModel):
    """운용사(GP) 집계 정보"""

    company_name: str = Field(..., description="운용사명")
    company_code: str = Field("", description="운용사 코드 (KOFIA)")
    fund_count: int = Field(..., description="운용 펀드 수")
    active_fund_count: int = Field(0, description="운용중 펀드 수")
    total_aum: Decimal | None = Field(None, description="총 AUM — 설정액 합계 (원)")
    asset_classes: list[str] = Field(default_factory=list, description="자산 클래스 목록")
    vintage_range: str | None = Field(None, description="빈티지 범위 (예: 2018~2024)")
    has_maturity_alert: bool = Field(False, description="만기 경고 펀드 존재 여부")
    data_sources: list[str] = Field(default_factory=lambda: ["kofia"], description="데이터 소스 목록")
    is_co_gp_count: int = Field(0, description="Co-GP 참여 펀드 수")
    pef_fund_count: int = Field(0, description="PEF 등록부 펀드 수")
    reference_date: str | None = Field(None, description="데이터 기준시점")
    logo_url: str | None = Field(None, description="운용사 로고 URL")


class GPListResponse(BaseModel):
    """운용사(GP) 목록 응답"""

    total: int
    page: int
    size: int
    items: list[GPListItem]
    reference_date: str | None = Field(None, description="데이터 기준시점")
