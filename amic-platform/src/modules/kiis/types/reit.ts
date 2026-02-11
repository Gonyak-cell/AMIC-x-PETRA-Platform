export type ReitType = "self_managed" | "entrusted";
export type ReitStatus = "authorized" | "operating" | "dissolved";

/** 목록 API 응답 아이템 (GET /reits → items[]) */
export interface REITsListItem {
  reits_code: string;
  reits_name: string;
  reits_type: string;
  management_company: string;
  total_assets: string | null;
  real_estate_ratio: string | null;
  has_asset_ratio_warning: boolean;
  status: string;
  is_listed: boolean;
}

/** 상세 API 응답 내 reits 객체 (GET /reits/{code} → .reits) */
export interface REITsItem extends REITsListItem {
  establishment_date: string | null;
  listing_date: string | null;
  real_estate_amount: string | null;
  dividend_rate: string | null;
  dividend_payout_ratio: string | null;
  net_income: string | null;
  total_dividend: string | null;
  employee_count: number | null;
  source_url: string;
}

/** 자산 아이템 (GET /reits/{code} → .assets[]) */
export interface REITsAssetItem {
  asset_name: string;
  asset_type: string;
  asset_value: string | null;
  asset_ratio: string | null;
  location: string;
  acquisition_date: string | null;
}

/** 상세 API 래퍼 응답 */
export interface REITsDetailResponse {
  reits: REITsItem;
  assets: REITsAssetItem[];
}

/** 목록 API 래퍼 응답 */
export interface REITsListResponse {
  total: number;
  page: number;
  size: number;
  items: REITsListItem[];
}

export interface ReitListParams {
  type?: ReitType;
  status?: ReitStatus;
  page?: number;
  size?: number;
}
