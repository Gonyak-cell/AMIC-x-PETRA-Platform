export type SurvivalStatus =
  | "active"
  | "audit_missing"
  | "dissolved"
  | "unicorn"
  | "unknown";

export interface PortfolioItem {
  id: number;
  investor_company_id: number;
  target_company_name: string;
  target_company_id: number | null;
  deal_id: number | null;
  survival_status: SurvivalStatus;
  last_audit_date: string | null;
  last_audit_rcept_no: string | null;
  dissolution_date: string | null;
  dissolution_rcept_no: string | null;
  estimated_valuation: string | null;
  is_unicorn: boolean;
  checked_at: string | null;
  notes: string | null;
}

export interface PortfolioListResponse {
  total: number;
  page: number;
  size: number;
  items: PortfolioItem[];
}

export interface PortfolioListParams {
  status?: SurvivalStatus;
  page?: number;
  size?: number;
}

export interface PortfolioSummary {
  total: number;
  active_count: number;
  audit_missing_count: number;
  dissolved_count: number;
  unicorn_count: number;
  unknown_count: number;
}

export interface SyncResponse {
  synced_count: number;
}

export interface SurvivalCheckResponse {
  portfolio_id: number;
  previous_status: SurvivalStatus;
  new_status: SurvivalStatus;
  checked_at: string;
}

export interface ValuationUpdateRequest {
  estimated_valuation: string;
}

export interface ValuationUpdateResponse {
  portfolio_id: number;
  target_company_name: string;
  estimated_valuation: string;
  is_unicorn: boolean;
  is_newly_unicorn: boolean;
  survival_status: SurvivalStatus;
}
