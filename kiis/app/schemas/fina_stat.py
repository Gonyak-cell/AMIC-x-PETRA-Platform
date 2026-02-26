"""금융위원회 기업 재무정보 (GetFinaStatInfoService_V2) 응답 스키마."""

from pydantic import BaseModel, Field


class SummaryFinancialItem(BaseModel):
    """요약재무제표 항목 (getSummFinaStat_V2)"""

    bas_dt: str = Field("", description="기준일자 (YYYYMMDD)")
    crno: str = Field("", description="법인등록번호")
    biz_year: str = Field("", description="사업연도")
    cur_cd: str = Field("KRW", description="통화코드")
    fncl_dcd: str = Field("", description="재무제표구분코드")
    fncl_dcd_nm: str = Field("", description="재무제표구분명 (연결/별도)")
    sale_amt: str = Field("", description="매출금액")
    bzop_pft: str = Field("", description="영업이익")
    icls_pal_clc_amt: str = Field("", description="포괄손익계산금액")
    crtm_npf: str = Field("", description="당기순이익")
    tast_amt: str = Field("", description="총자산금액")
    tdbt_amt: str = Field("", description="총부채금액")
    tcpt_amt: str = Field("", description="총자본금액")
    cptl_amt: str = Field("", description="자본금액")
    debt_rto: str = Field("", description="부채비율")


class FinaStatItem(BaseModel):
    """재무상태표/손익계산서 항목 (getBs_V2, getIncoStat_V2)"""

    bas_dt: str = Field("", description="기준일자")
    crno: str = Field("", description="법인등록번호")
    biz_year: str = Field("", description="사업연도")
    cur_cd: str = Field("KRW", description="통화코드")
    fncl_dcd: str = Field("", description="재무제표구분코드")
    fncl_dcd_nm: str = Field("", description="재무제표구분명")
    acit_id: str = Field("", description="계정과목ID")
    acit_nm: str = Field("", description="계정과목명")
    thqr_acit_amt: str = Field("", description="당분기계정과목금액")
    crtm_acit_amt: str = Field("", description="당기계정과목금액")
    lsqt_acit_amt: str = Field("", description="전분기계정과목금액")
    pvtr_acit_amt: str = Field("", description="전기계정과목금액")
    bpvtr_acit_amt: str = Field("", description="전전기계정과목금액")


class SummaryFinancialResponse(BaseModel):
    """요약재무 KPI 응답"""

    source: str = Field("DATA_GO_KR", description="데이터 출처 (DART | DATA_GO_KR)")
    biz_year: str = Field("", description="사업연도")
    sale_amt: str | None = Field(None, description="매출금액")
    bzop_pft: str | None = Field(None, description="영업이익")
    crtm_npf: str | None = Field(None, description="당기순이익")
    tast_amt: str | None = Field(None, description="총자산금액")
    tdbt_amt: str | None = Field(None, description="총부채금액")
    tcpt_amt: str | None = Field(None, description="총자본금액")
    cptl_amt: str | None = Field(None, description="자본금액")
    debt_rto: str | None = Field(None, description="부채비율")
