"""금융위원회 기업기본정보 (GetCorpBasicInfoService_V2) 응답 스키마."""

from pydantic import BaseModel, Field


class CorpOutlineItem(BaseModel):
    """기업 개요 (getCorpOutline_V2)"""

    crno: str = Field("", description="법인등록번호")
    corp_nm: str = Field("", description="기업명")
    corp_nm_en: str = Field("", description="영문명")
    pban_cmp_nm: str = Field("", description="공시기업명")
    rep_nm: str = Field("", description="대표자")
    mkt_dcd: str = Field("", description="시장구분코드 (P:유가, K:코스닥, N:코넥스, E:기타)")
    mkt_dcd_nm: str = Field("", description="시장구분명")
    bzno: str = Field("", description="사업자등록번호")
    ozpno: str = Field("", description="우편번호")
    bsadr: str = Field("", description="기본주소")
    dtadr: str = Field("", description="상세주소")
    hmpg_url: str = Field("", description="홈페이지")
    tlno: str = Field("", description="전화번호")
    fxno: str = Field("", description="팩스번호")
    sic_nm: str = Field("", description="업종명")
    est_dt: str = Field("", description="설립일 (YYYYMMDD)")
    stac_mm: str = Field("", description="결산월")
    xchg_lstg_dt: str = Field("", description="유가증권 상장일")
    kosdaq_lstg_dt: str = Field("", description="코스닥 상장일")
    krx_lstg_dt: str = Field("", description="KRX 상장일")
    smenp_yn: str = Field("", description="중소기업 여부")
    mntr_bnk_nm: str = Field("", description="주거래은행")
    emp_cnt: str = Field("", description="종업원수")
    avg_cnwk_term: str = Field("", description="평균근속연수")
    avg_slry_amt: str = Field("", description="1인평균급여액")
    audpn_nm: str = Field("", description="회계감사인")
    audt_opnn: str = Field("", description="감사의견")
    main_biz_nm: str = Field("", description="주요사업")
    fss_corp_unq_no: str = Field("", description="금감원 고유번호")


class AffiliateItem(BaseModel):
    """계열회사 (getAffiliate_V2)"""

    bas_dt: str = Field("", description="기준일자")
    crno: str = Field("", description="법인등록번호")
    afil_cmpy_nm: str = Field("", description="계열회사명")
    afil_cmpy_crno: str = Field("", description="계열회사 법인등록번호")
    lstg_yn: str = Field("", description="상장여부")


class SubsidiaryItem(BaseModel):
    """연결대상 종속기업 (getConsSubsComp_V2)"""

    bas_dt: str = Field("", description="기준일자")
    crno: str = Field("", description="법인등록번호")
    sbrd_enp_nm: str = Field("", description="종속기업명")
    sbrd_enp_estb_dt: str = Field("", description="설립일자")
    sbrd_enp_adr: str = Field("", description="주소")
    sbrd_enp_main_biz: str = Field("", description="주요사업")
    sbrd_enp_tast_amt: str = Field("", description="총자산금액")
    dnt_rlt_bsis: str = Field("", description="지배관계근거")
    main_sbrd_enp_yn: str = Field("", description="주요종속기업여부")


class CorpBasicInfoResponse(BaseModel):
    """기업 기본정보 통합 응답"""

    outline: CorpOutlineItem | None = Field(None, description="기업 개요")
    affiliates: list[AffiliateItem] = Field(default_factory=list, description="계열회사")
    subsidiaries: list[SubsidiaryItem] = Field(default_factory=list, description="종속기업")
