/** GP(운용사) 목록 아이템 — KOFIA 펀드 데이터의 company_name별 그룹화 */
export interface GPListItem {
  company_name: string;
  company_code: string;
  fund_count: number;
  active_fund_count: number;
  total_aum: string | null;
  asset_classes: string[];
  vintage_range: string | null;
  has_maturity_alert: boolean;
  data_sources?: string[];
  is_co_gp_count?: number;
  pef_fund_count?: number;
  reference_date?: string | null;
}

/** GP 목록 API 응답 */
export interface GPListResponse {
  total: number;
  page: number;
  size: number;
  items: GPListItem[];
  reference_date?: string | null;
}

export type GPSortField = "total_aum" | "fund_count" | "company_name";

/** GP 목록 API 쿼리 파라미터 */
export interface GPListParams {
  company_name?: string;
  asset_class?: string;
  data_source?: string;
  sort_by?: GPSortField;
  sort_order?: "asc" | "desc";
  page?: number;
  size?: number;
}
