from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

# --- 리츠 자산 ---


class REITsAssetItem(BaseModel):
    """리츠 보유 자산 정보"""

    asset_name: str = Field(..., description="자산명")
    asset_type: str = Field(..., description="자산 유형 (office/logistics/residential/retail/hotel/other)")
    asset_value: Decimal | None = Field(None, description="자산 가액 (백만원)")
    asset_ratio: Decimal | None = Field(None, description="자산 비율 (%)")
    location: str = Field("", description="소재지")
    acquisition_date: date | None = Field(None, description="취득일")


class REITsAssetListResponse(BaseModel):
    """리츠 자산 목록 응답"""

    total: int
    items: list[REITsAssetItem]


# --- 리츠 ---


class REITsItem(BaseModel):
    """리츠 상세 정보"""

    reits_code: str = Field(..., description="리츠 코드")
    reits_name: str = Field(..., description="리츠명")
    reits_type: str = Field(..., description="리츠 유형 (self_managed/entrusted)")
    management_company: str = Field("", description="자산관리회사명")
    establishment_date: date | None = Field(None, description="설립인가일")
    listing_date: date | None = Field(None, description="상장일")
    total_assets: Decimal | None = Field(None, description="총자산 (백만원)")
    real_estate_amount: Decimal | None = Field(None, description="부동산 자산액 (백만원)")
    real_estate_ratio: Decimal | None = Field(None, description="부동산 비율 (%)")
    has_asset_ratio_warning: bool = Field(False, description="부동산 70% 미달 경고")
    dividend_rate: Decimal | None = Field(None, description="배당수익률 (%)")
    dividend_payout_ratio: Decimal | None = Field(None, description="배당성향 (배당금/당기순이익, %)")
    net_income: Decimal | None = Field(None, description="당기순이익 (백만원)")
    total_dividend: Decimal | None = Field(None, description="배당금 총액 (백만원)")
    employee_count: int | None = Field(None, description="임직원 수")
    status: str = Field("authorized", description="상태 (authorized/operating/dissolved)")
    is_listed: bool = Field(False, description="상장 여부")
    source_url: str = Field("", description="출처 URL")


class REITsListItem(BaseModel):
    """리츠 목록 아이템 (간략 정보)"""

    reits_code: str = Field(..., description="리츠 코드")
    reits_name: str = Field(..., description="리츠명")
    reits_type: str = Field(..., description="리츠 유형 (self_managed/entrusted)")
    management_company: str = Field("", description="자산관리회사명")
    total_assets: Decimal | None = Field(None, description="총자산 (백만원)")
    real_estate_ratio: Decimal | None = Field(None, description="부동산 비율 (%)")
    has_asset_ratio_warning: bool = Field(False, description="부동산 70% 미달 경고")
    status: str = Field("authorized", description="상태")
    is_listed: bool = Field(False, description="상장 여부")


class REITsListResponse(BaseModel):
    """리츠 목록 응답"""

    total: int
    page: int
    size: int
    items: list[REITsListItem]


class REITsDetailResponse(BaseModel):
    """리츠 상세 응답 (자산 내역 포함)"""

    reits: REITsItem
    assets: list[REITsAssetItem] = Field(default_factory=list, description="보유 자산 목록")
