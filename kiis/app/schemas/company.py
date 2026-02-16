from pydantic import BaseModel, ConfigDict, Field


class CompanyItem(BaseModel):
    """기업 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="정식명칭")
    corp_name_eng: str | None = Field(None, description="영문명칭")
    stock_name: str | None = Field(None, description="종목명")
    stock_code: str | None = Field(None, description="종목코드")
    ceo_nm: str | None = Field(None, description="대표자명")
    corp_cls: str | None = Field(None, description="법인구분 (Y:유가, K:코스닥, N:코넥스, E:기타)")
    jurir_no: str | None = Field(None, description="법인등록번호")
    bizr_no: str | None = Field(None, description="사업자등록번호")
    adres: str | None = Field(None, description="주소")
    hm_url: str | None = Field(None, description="홈페이지")
    ir_url: str | None = Field(None, description="IR 홈페이지")
    phn_no: str | None = Field(None, description="전화번호")
    induty_code: str | None = Field(None, description="업종코드")
    est_dt: str | None = Field(None, description="설립일 (YYYYMMDD)")
    acc_mt: str | None = Field(None, description="결산월")


class CompanyListItem(BaseModel):
    """기업 목록 아이템 (간략 정보)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="정식명칭")
    stock_name: str | None = Field(None, description="종목명")
    stock_code: str | None = Field(None, description="종목코드")
    corp_cls: str | None = Field(None, description="법인구분")


class CompanyListResponse(BaseModel):
    """기업 목록 응답"""

    total: int
    page: int
    size: int
    items: list[CompanyListItem]


class CompanyCreateRequest(BaseModel):
    """기업 등록 요청 (DART 동기화용)"""

    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="정식명칭")
    corp_name_eng: str | None = None
    stock_name: str | None = None
    stock_code: str | None = None
    ceo_nm: str | None = None
    corp_cls: str | None = None
    jurir_no: str | None = None
    bizr_no: str | None = None
    adres: str | None = None
    hm_url: str | None = None
    ir_url: str | None = None
    phn_no: str | None = None
    induty_code: str | None = None
    est_dt: str | None = None
    acc_mt: str | None = None
