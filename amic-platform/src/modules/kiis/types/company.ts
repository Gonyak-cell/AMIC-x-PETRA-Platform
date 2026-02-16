export type CorpCls = "Y" | "K" | "N" | "E";

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

/** 재무제표 래퍼 응답 */
export interface FinancialListResponse {
  items: FinancialStatement[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface CompanyListParams {
  search?: string;
  corp_cls?: CorpCls;
  page?: number;
  size?: number;
}

export interface FinancialParams {
  bsns_year: string;
  reprt_code?: string;
  fs_div?: "CFS" | "OFS";
}
