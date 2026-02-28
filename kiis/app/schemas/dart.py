from pydantic import BaseModel, Field


# --- 기업 개황 ---
class CompanyInfo(BaseModel):
    corp_code: str = Field(..., description="고유번호")
    corp_name: str = Field(..., description="정식명칭")
    corp_name_eng: str = Field("", description="영문명칭")
    stock_name: str = Field("", description="종목명")
    stock_code: str = Field("", description="종목코드")
    ceo_nm: str = Field("", description="대표자명")
    corp_cls: str = Field("", description="법인구분 (Y:유가, K:코스닥, N:코넥스, E:기타)")
    jurir_no: str = Field("", description="법인등록번호")
    bizr_no: str = Field("", description="사업자등록번호")
    adres: str = Field("", description="주소")
    hm_url: str = Field("", description="홈페이지")
    ir_url: str = Field("", description="IR 홈페이지")
    phn_no: str = Field("", description="전화번호")
    fax_no: str = Field("", description="팩스번호")
    induty_code: str = Field("", description="업종코드")
    est_dt: str = Field("", description="설립일 (YYYYMMDD)")
    acc_mt: str = Field("", description="결산월")


class CompanyListItem(BaseModel):
    corp_code: str
    corp_name: str
    stock_code: str = ""
    modify_date: str = ""


class CompanyListResponse(BaseModel):
    total: int
    items: list[CompanyListItem]


# --- 공시 검색 ---
class DisclosureItem(BaseModel):
    corp_code: str = Field("", description="고유번호")
    corp_name: str = Field("", description="종목명")
    corp_cls: str = Field("", description="법인구분")
    report_nm: str = Field("", description="보고서명")
    rcept_no: str = Field("", description="접수번호")
    flr_nm: str = Field("", description="공시 제출인명")
    rcept_dt: str = Field("", description="접수일자 (YYYYMMDD)")
    rm: str = Field("", description="비고")


class DisclosureSearchParams(BaseModel):
    corp_code: str | None = Field(None, description="고유번호")
    bgn_de: str | None = Field(None, description="시작일 (YYYYMMDD)")
    end_de: str | None = Field(None, description="종료일 (YYYYMMDD)")
    last_reprt_at: str | None = Field(None, description="최종보고서 검색 여부 (Y/N)")
    pblntf_ty: str | None = Field(None, description="공시유형 (A:정기, B:주요사항, ...)")
    page_no: int = Field(1, ge=1, description="페이지 번호")
    page_count: int = Field(20, ge=1, le=100, description="페이지당 건수")


class DisclosureListResponse(BaseModel):
    page_no: int
    page_count: int
    total_count: int
    total_page: int
    items: list[DisclosureItem]


# --- 재무제표 ---
class FinancialStatementItem(BaseModel):
    rcept_no: str = Field("", description="접수번호")
    reprt_code: str = Field("", description="보고서 코드")
    bsns_year: str = Field("", description="사업연도")
    corp_code: str = Field("", description="고유번호")
    sj_div: str = Field("", description="재무제표구분 (BS:재무상태표, IS:손익계산서, ...)")
    sj_nm: str = Field("", description="재무제표명")
    account_id: str = Field("", description="계정ID")
    account_nm: str = Field("", description="계정명")
    account_detail: str = Field("", description="계정상세")
    thstrm_nm: str = Field("", description="당기명")
    thstrm_amount: str = Field("", description="당기금액")
    frmtrm_nm: str = Field("", description="전기명")
    frmtrm_amount: str = Field("", description="전기금액")
    bfefrmtrm_nm: str = Field("", description="전전기명")
    bfefrmtrm_amount: str = Field("", description="전전기금액")
    ord: str = Field("", description="계정과목 정렬순서")


class FinancialSearchParams(BaseModel):
    corp_code: str = Field(..., description="고유번호")
    bsns_year: str = Field(..., description="사업연도 (YYYY)")
    reprt_code: str = Field("11011", description="보고서 코드 (11011:사업보고서, 11012:반기, 11013:1분기, 11014:3분기)")
    fs_div: str = Field("CFS", description="개별/연결 (CFS:연결, OFS:개별)")


class FinancialListResponse(BaseModel):
    source: str = Field("DART", description="데이터 출처 (DART | DATA_GO_KR | NONE)")
    items: list[FinancialStatementItem]


# --- 제재 내역 ---
class SanctionItem(BaseModel):
    corp_code: str = Field("", description="고유번호")
    corp_name: str = Field("", description="회사명")
    sanctions_type: str = Field("", description="제재유형")
    sanctions_detail: str = Field("", description="제재내용")
    sanctions_date: str = Field("", description="제재일자")
    sanctions_agency: str = Field("", description="제재기관")


class SanctionListResponse(BaseModel):
    items: list[SanctionItem]


# --- 대량보유상황보고서 ---
class MajorHoldingItem(BaseModel):
    rcept_no: str = Field("", description="접수번호")
    rcept_dt: str = Field("", description="접수일자 (YYYYMMDD)")
    corp_code: str = Field("", description="고유번호")
    corp_name: str = Field("", description="법인명")
    report_tp: str = Field("", description="보고구분")
    repror: str = Field("", description="대표보고자")
    stkqy: str = Field("", description="보유주식수")
    stkrt: str = Field("", description="보유비율 (%)")
    stkqy_irds: str = Field("", description="보유주식수 증감")
    stkrt_irds: str = Field("", description="보유비율 증감")
    ctr_stkqy: str = Field("", description="주요체결 주식수")
    ctr_stkrt: str = Field("", description="주요체결 지분율")
    report_resn: str = Field("", description="보고사유")


class MajorHoldingListResponse(BaseModel):
    page_no: int
    page_count: int
    total_count: int
    total_page: int
    items: list[MajorHoldingItem]


class HoldingSyncResponse(BaseModel):
    total_fetched: int = 0
    new_records: int = 0
    updated_records: int = 0
    deals_created: int = 0
    linked_disclosures: int = 0
    errors: list[str] = Field(default_factory=list)


# --- 임원·주요주주 소유보고 ---
class ElestockItem(BaseModel):
    rcept_no: str = Field("", description="접수번호")
    rcept_dt: str = Field("", description="접수일자 (YYYYMMDD)")
    corp_code: str = Field("", description="고유번호")
    corp_name: str = Field("", description="법인명")
    repror: str = Field("", description="보고자명")
    isu_exctv_rgist_at: str = Field("", description="임원 등록 여부 (Y/N)")
    isu_exctv_ofcps: str = Field("", description="직책")
    isu_main_shrholdr: str = Field("", description="주요주주 여부 (Y/N)")
    sp_stock_lmp_cnt: str = Field("", description="소유 주식수")
    sp_stock_lmp_irds_cnt: str = Field("", description="소유 주식수 증감")
    sp_stock_lmp_rate: str = Field("", description="소유 비율 (%)")
    sp_stock_lmp_irds_rate: str = Field("", description="소유 비율 증감")
    ctr_stkqy: str = Field("", description="특정증권등 소유 주식수")
    ctr_stkrt: str = Field("", description="특정증권등 소유 비율")
    report_resn: str = Field("", description="변동사유")


class ElestockListResponse(BaseModel):
    items: list[ElestockItem]


class ElestockSyncResponse(BaseModel):
    total_fetched: int = 0
    new_records: int = 0
    updated_records: int = 0
    deals_created: int = 0
    linked_disclosures: int = 0
    errors: list[str] = Field(default_factory=list)
