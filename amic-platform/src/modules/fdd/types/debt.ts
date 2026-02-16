// ── Enums ────────────────────────────────────────────────

export type DebtStatus = "DRAFT" | "REVIEW" | "APPROVED";

export type DebtItemType =
  | "GROSS_DEBT"
  | "CASH"
  | "DEBT_LIKE"
  | "CASH_LIKE";

export type DebtItemStatus =
  | "CANDIDATE"
  | "PROPOSED"
  | "APPROVED"
  | "REJECTED";

// ── Debt Item ───────────────────────────────────────────

export interface DebtItemRead {
  id: string;
  net_debt_calculation_id: string;
  deal_id: string;
  item_type: DebtItemType;
  description: string;
  amount: string; // Decimal as string — NEVER number
  source_account_code: string | null;
  source_account_name: string | null;
  detection_method: string;
  confidence_score: string | null;
  status: DebtItemStatus;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface DebtItemCreate {
  item_type: DebtItemType;
  description: string;
  amount: string;
  source_account_code?: string | null;
  source_account_name?: string | null;
}

export interface DebtItemUpdate {
  item_type?: DebtItemType;
  description?: string;
  amount?: string;
  status?: DebtItemStatus;
  rejection_reason?: string;
}

export interface DebtItemApprove {
  approved_by: string;
}

// ── Category Breakdown ──────────────────────────────────

export interface DebtCategoryBreakdown {
  [category: string]: {
    total_amount: string;
    item_type: DebtItemType;
    items?: string[];
  };
}

// ── Net Debt Calculation ────────────────────────────────

export interface NetDebtCalculationRead {
  id: string;
  deal_id: string;
  snapshot_id: string;
  gross_debt: string;
  cash_and_equivalents: string;
  net_debt: string;
  debt_like_total: string;
  cash_like_total: string;
  adjusted_net_debt: string;
  include_lease_liabilities: boolean;
  include_deferred_revenue: boolean;
  balance_check_error: string;
  category_breakdown: DebtCategoryBreakdown;
  engine_version: string;
  status: DebtStatus;
  items: DebtItemRead[];
  created_at: string;
  updated_at: string;
}

export interface NetDebtRunRequest {
  snapshot_id: string;
  include_lease_liabilities?: boolean;
  include_deferred_revenue?: boolean;
}

// ── Bridge Summary ──────────────────────────────────────

export interface NetDebtBridgeSummary {
  gross_debt: string;
  cash_and_equivalents: string;
  net_debt: string;
  debt_like_items: DebtItemRead[];
  cash_like_items: DebtItemRead[];
  debt_like_total: string;
  cash_like_total: string;
  adjusted_net_debt: string;
  balance_check_error: string;
  is_balanced: boolean;
}
