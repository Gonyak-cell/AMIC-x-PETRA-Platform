// ── Enums ────────────────────────────────────────────────

export type NWCStatus = "DRAFT" | "REVIEW" | "APPROVED";

export type NWCClassification = "ABOVE_LINE" | "BELOW_LINE" | "EXCLUDED";

export type PegMethod =
  | "LTM_AVERAGE"
  | "TTM"
  | "LAST_MONTH"
  | "MAX"
  | "MIN"
  | "CUSTOM";

// ── NWC Line Item ───────────────────────────────────────

export interface NWCLineItemRead {
  id: string;
  nwc_calculation_id: string;
  deal_id: string;
  account_code: string;
  account_name: string;
  line_item_category: string;
  classification: NWCClassification;
  amount: string; // Decimal as string — NEVER number
  monthly_amounts: Record<string, string>;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface NWCLineItemUpdate {
  classification: NWCClassification;
}

// ── NWC Calculation ─────────────────────────────────────

export interface NWCCalculationRead {
  id: string;
  deal_id: string;
  snapshot_id: string;
  total_current_assets: string; // Decimal as string
  total_current_liabilities: string;
  net_working_capital: string;
  peg_method: PegMethod;
  peg_target: string;
  peg_delta: string;
  monthly_trend: Record<string, MonthlyTrendEntry>;
  category_breakdown: Record<string, unknown>;
  engine_version: string;
  status: NWCStatus;
  line_items: NWCLineItemRead[];
  created_at: string;
  updated_at: string;
}

export interface MonthlyTrendEntry {
  current_assets: string;
  current_liabilities: string;
  nwc: string;
}

export interface NWCRunRequest {
  snapshot_id: string;
  peg_method?: PegMethod;
  custom_peg_value?: string | null;
}

// ── NWC Summary ─────────────────────────────────────────

export interface NWCSummary {
  net_working_capital: string;
  total_current_assets: string;
  total_current_liabilities: string;
  peg_method: PegMethod;
  peg_target: string;
  peg_delta: string;
  above_line_items: NWCLineItemRead[];
  below_line_items: NWCLineItemRead[];
  is_above_target: boolean;
}

// ── Peg Simulation ──────────────────────────────────────

export interface PegSimulationRequest {
  peg_method: PegMethod;
  custom_value?: string | null;
}

export interface PegSimulationResult {
  method: PegMethod;
  target_nwc: string;
  delta: string;
  description: string;
}

export interface PegSimulationResponse {
  reference_nwc: string;
  scenarios: PegSimulationResult[];
}
