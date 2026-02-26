export type CorpCls = "Y" | "K" | "N" | "E";
export type SearchType = "name" | "stock_code" | "jurir_no" | "bizr_no";

/** 기업 목록 아이템 (GET /companies → items[]) */
export interface Company {
  id: number;
  corp_code: string;
  corp_name: string;
  stock_name: string | null;
  stock_code: string | null;
  corp_cls: CorpCls | null;
}

/** 기업 상세 (GET /companies/{corpCode}) */
export interface CompanyDetail extends Company {
  corp_name_eng: string | null;
  ceo_nm: string | null;
  adres: string | null;
  hm_url: string | null;
  ir_url: string | null;
  phn_no: string | null;
  induty_code: string | null;
  est_dt: string | null;
  acc_mt: string | null;
  jurir_no: string | null;
  bizr_no: string | null;
}

/** 재무제표 아이템 (GET /dart/companies/{corpCode}/financials → items[]) */
export interface FinancialStatement {
  rcept_no: string;
  reprt_code: string;
  bsns_year: string;
  corp_code: string;
  sj_div: string;
  sj_nm: string;
  account_id: string;
  account_nm: string;
  account_detail: string;
  thstrm_nm: string;
  thstrm_amount: string;
  frmtrm_nm: string;
  frmtrm_amount: string;
  bfefrmtrm_nm: string;
  bfefrmtrm_amount: string;
  ord: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface CompanyListParams {
  search?: string;
  search_type?: SearchType;
  /** 쉼표 구분 복수 선택 가능 (예: "Y,K") */
  corp_cls?: string;
  page?: number;
  size?: number;
}

export interface FinancialParams {
  bsns_year: string;
  reprt_code?: string;
  fs_div?: "CFS" | "OFS";
}

/** 재무 요약 KPI (financial-summary 엔드포인트) */
export interface FinancialSummary {
  source: "DART" | "DATA_GO_KR" | "NONE";
  biz_year: string;
  sale_amt: string | null;
  bzop_pft: string | null;
  crtm_npf: string | null;
  tast_amt: string | null;
  tdbt_amt: string | null;
  tcpt_amt: string | null;
  cptl_amt: string | null;
  debt_rto: string | null;
}

/** 재무제표 래퍼 응답 (source 포함) */
export interface FinancialListResponseWithSource {
  source: "DART" | "DATA_GO_KR" | "NONE";
  items: FinancialStatement[];
}

/** 기업 개요 (공공데이터포털 GetCorpBasicInfoService_V2) */
export interface CorpOutlineItem {
  crno: string;
  corp_nm: string;
  corp_nm_en: string;
  pban_cmp_nm: string;
  rep_nm: string;
  mkt_dcd: string;
  mkt_dcd_nm: string;
  bzno: string;
  ozpno: string;
  bsadr: string;
  dtadr: string;
  hmpg_url: string;
  tlno: string;
  fxno: string;
  sic_nm: string;
  est_dt: string;
  stac_mm: string;
  xchg_lstg_dt: string;
  kosdaq_lstg_dt: string;
  krx_lstg_dt: string;
  smenp_yn: string;
  mntr_bnk_nm: string;
  emp_cnt: string;
  avg_cnwk_term: string;
  avg_slry_amt: string;
  audpn_nm: string;
  audt_opnn: string;
  main_biz_nm: string;
  fss_corp_unq_no: string;
}

/** 계열회사 (getAffiliate_V2) */
export interface AffiliateItem {
  bas_dt: string;
  crno: string;
  afil_cmpy_nm: string;
  afil_cmpy_crno: string;
  lstg_yn: string;
}

/** 연결대상 종속기업 (getConsSubsComp_V2) */
export interface SubsidiaryItem {
  bas_dt: string;
  crno: string;
  sbrd_enp_nm: string;
  sbrd_enp_estb_dt: string;
  sbrd_enp_adr: string;
  sbrd_enp_main_biz: string;
  sbrd_enp_tast_amt: string;
  dnt_rlt_bsis: string;
  main_sbrd_enp_yn: string;
}

/** 기업 기본정보 통합 응답 */
export interface CorpBasicInfo {
  outline: CorpOutlineItem | null;
  affiliates: AffiliateItem[];
  subsidiaries: SubsidiaryItem[];
}
