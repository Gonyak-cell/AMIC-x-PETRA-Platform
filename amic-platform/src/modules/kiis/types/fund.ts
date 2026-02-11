export type FundType = "blind" | "project";

/** 목록 API 응답 아이템 (GET /kofia/funds → items[]) */
export interface FundListItem {
  fund_code: string;
  fund_name: string;
  fund_type: string;
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

export interface FundListParams {
  company_name?: string;
  fund_type?: FundType;
  page?: number;
  size?: number;
}
