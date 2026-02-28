// SI 매핑 관련 TypeScript 타입 정의

export type SICompanyRelation = "DIRECT" | "BACKWARD" | "FORWARD";

export interface SICompany {
  id: string;
  company_name: string;
  ksic_codes: string[] | null;
  revenue: number | null;
  revenue_year: number | null;
  has_investment_history: boolean;
  description: string | null;

  // 재무정보 (금융위 getSummFinaStat_V2)
  operating_profit: number | null;
  net_income: number | null;
  total_assets: number | null;
  total_debt: number | null;
  total_equity: number | null;
  capital_amount: number | null;
  debt_ratio: number | null;
  pretax_income: number | null;

  // 기업기본정보 (금융위 getCorpOutline_V2)
  representative: string | null;
  founded_date: string | null;
  address: string | null;
  homepage: string | null;
  employee_count: string | null;
  industry_name: string | null;
  main_business: string | null;
  market_type: string | null;
  market_type_name: string | null;
}

export interface SICandidate {
  company: SICompany;
  relation: SICompanyRelation;
  io_code: string | null;
  io_name: string | null;
  transaction_value: number | null;
}

export interface ValueChainPanel {
  io_code: string;
  io_name: string;
  transaction_value: number;
  companies: SICompany[];
}

export interface SIMappingResponse {
  target_ksic_codes: string[];
  target_io_codes: string[];
  direct_peers: SICompany[];
  backward_chain: ValueChainPanel[];
  forward_chain: ValueChainPanel[];
  all_candidates: SICandidate[];
}

export interface SIMappingRequest {
  ksic_codes: string[];
  top_n?: number;
  max_companies_per_panel?: number;
  min_revenue?: number | null;
  require_investment_history?: boolean;
}

export interface KsicSuggestion {
  code: string;
  name: string;
}

export interface BulkAddBuyersRequest {
  si_company_ids: string[];
}

export interface BulkAddBuyersResponse {
  added_count: number;
  skipped_count: number;
  buyer_ids: string[];
}

export interface SIDataStats {
  si_companies_count: number;
  ksic_io_mappings_count: number;
  io_transactions_count: number;
  revenue_count: number;
  fina_stat_count: number;
  corp_basic_count: number;
  is_seeded: boolean;
}

// ── 딥다이브 ──────────────────────────────────────────────

export interface CompanyOverview {
  corp_code: string;
  corp_name: string;
  ceo_nm: string;
  est_dt: string;
  induty_code: string;
  adres: string;
  hm_url: string;
}

export interface FinancialSummary {
  bsns_year: string;
  revenue: number | null;
  operating_income: number | null;
  net_income: number | null;
  total_assets: number | null;
}

export interface DeepDiveDisclosure {
  rcept_dt: string;
  report_nm: string;
  rcept_no: string;
}

export interface SanctionItem {
  date: string;
  type: string;
  content: string;
}

export interface DeepDiveResponse {
  company: SICompany;
  overview: CompanyOverview | null;
  financials: FinancialSummary[];
  disclosures: DeepDiveDisclosure[];
  sanctions: SanctionItem[];
  dart_available: boolean;
}
