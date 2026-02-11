export type CorpCls = "Y" | "K" | "N" | "E";

export interface Company {
  corp_code: string;
  corp_name: string;
  stock_code: string | null;
  corp_cls: CorpCls;
  ceo_nm: string | null;
  address: string | null;
}

export interface CompanyDetail extends Company {
  industry: string | null;
  est_dt: string | null;
  homepage: string | null;
  ir_url: string | null;
  phn_no: string | null;
  fax_no: string | null;
  jurir_no: string | null;
  bizr_no: string | null;
}

export interface FinancialStatement {
  account_nm: string;
  thstrm_amount: number | null;
  frmtrm_amount: number | null;
  bfefrmtrm_amount: number | null;
}

export interface Disclosure {
  rcept_no: string;
  report_nm: string;
  rcept_dt: string;
  flr_nm: string;
  viewer_url: string | null;
  pdf_url: string | null;
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
  bsns_year?: string;
  reprt_code?: string;
}
