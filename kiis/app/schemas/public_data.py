from decimal import Decimal

from pydantic import BaseModel, Field


class GPRegistryItem(BaseModel):
    """공공데이터포털 자산운용사 정보 (금융통계 + 기본정보 조합)"""

    company_name: str = Field(..., description="운용사명")
    company_name_en: str = Field("", description="영문명")
    finance_company_code: str = Field("", description="금융회사코드")
    business_registration_no: str = Field("", description="사업자등록번호")
    corporation_registration_no: str = Field("", description="법인등록번호")
    established_date: str = Field("", description="설립일자")
    address: str = Field("", description="주소")
    phone: str = Field("", description="연락처")
    employee_count: int | None = Field(None, description="임직원수")
    capital: Decimal | None = Field(None, description="자본금 (백만원)")
    total_assets: Decimal | None = Field(None, description="총자산 (백만원)")
    aum: Decimal | None = Field(None, description="운용자산 AUM (백만원)")
    fund_count: int | None = Field(None, description="운용 펀드수")
    operating_revenue: Decimal | None = Field(None, description="영업수익 (백만원)")
    authorization_date: str = Field("", description="인가일자")
    data_date: str = Field("", description="데이터 기준일")
    source: str = Field("data.go.kr", description="데이터 출처")


class GPRegistryListResponse(BaseModel):
    """자산운용사 목록 응답"""

    total: int
    page: int
    size: int
    items: list[GPRegistryItem]


class GPSyncResponse(BaseModel):
    """GP 프로파일 동기화 결과 응답"""

    total_api_items: int = Field(0, description="API에서 조회된 GP 수")
    created: int = Field(0, description="신규 생성된 Company 수")
    updated: int = Field(0, description="GP 프로파일 업데이트된 Company 수")
    aliases_added: int = Field(0, description="자동 등록된 별칭 수")
    errors: list[str] = Field(default_factory=list, description="에러 발생 GP 목록")
