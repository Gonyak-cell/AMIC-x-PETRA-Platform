export type MarketingStage =
  | "IDENTIFIED"
  | "EMAIL_SENT"
  | "PHONE_CALL"
  | "ADVISOR_MEETING"
  | "NDA_SIGNED"
  | "TARGET_MEETING"
  | "CIM_SENT"
  | "DD_STARTED";

export interface MarketingLog {
  id: string;
  buyer_id: string;
  transaction_id: string;
  stage: MarketingStage;
  log_date: string;
  content: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarketingLogCreate {
  stage: MarketingStage;
  log_date: string;
  content?: string;
}

export interface MarketingLogUpdate {
  stage?: MarketingStage;
  log_date?: string;
  content?: string;
}

export interface BuyerStageSummary {
  buyer_id: string;
  stages: Partial<Record<MarketingStage, string | null>>;
}

export interface DartCompanySuggestion {
  corp_code: string;
  corp_name: string;
  stock_code: string | null;
}

export interface DartFinancialSummary {
  revenue: string | null;
  operating_profit: string | null;
  net_income: string | null;
  debt_ratio: string | null;
  fiscal_year: string | null;
}
