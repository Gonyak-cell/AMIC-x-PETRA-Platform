export type FundType = "blind" | "project";
export type LegalType = "professional_private" | "general_private" | "public";
export type AssetClass = "vc" | "pef" | "real_estate" | "infra" | "mezzanine" | "fund_of_funds";
export type FundStatus = "active" | "harvest" | "liquidated";

/** 목록 API 응답 아이템 (GET /kofia/funds → items[]) */
export interface FundListItem {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  legal_type: string;
  asset_class: string;
  fund_status: string;
  company_name: string;
  total_amount: string | null;
  vintage_year: number | null;
  is_maturity_alert: boolean;
}

/** 상세 API 응답 내 fund 객체 (GET /kofia/funds/{code} → .fund) */
export interface FundItem extends FundListItem {
  fund_category: string;
  company_code: string;
  management_fee_rate: string | null;
  performance_fee_rate: string | null;
  established_date: string | null;
  maturity_date: string | null;
  is_active: boolean;
  description: string;
  source_url: string;
  corp_code?: string;
}

/** 매니저 아이템 (GET /kofia/funds/{code} → .managers[]) */
export interface FundManagerItem {
  manager_name: string;
  position: string;
  role: string;
  career_years: number | null;
  education: string;
  certifications: string;
  appointed_date: string | null;
  resigned_date: string | null;
  is_active: boolean;
}

/** 상세 API 래퍼 응답 */
export interface FundDetailResponse {
  fund: FundItem;
  managers: FundManagerItem[];
}

/** 목록 API 래퍼 응답 */
export interface FundListResponse {
  total: number;
  page: number;
  size: number;
  items: FundListItem[];
}

export interface FundManagerListResponse {
  total: number;
  items: FundManagerItem[];
}

export type FundSortField = "total_amount" | "vintage_year" | "fund_name" | "company_name";

export interface FundListParams {
  company_name?: string;
  fund_name?: string;
  fund_type?: string;
  legal_type?: string;
  asset_class?: string;
  fund_status?: string;
  vintage_from?: number;
  vintage_to?: number;
  amount_min?: number;
  amount_max?: number;
  sort_by?: FundSortField;
  sort_order?: "asc" | "desc";
  page?: number;
  size?: number;
}
