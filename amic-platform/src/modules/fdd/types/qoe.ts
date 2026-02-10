// ── Enums ────────────────────────────────────────────────

export type QoEStatus = "DRAFT" | "REVIEW" | "APPROVED";

export type AdjustmentCategory =
  | "NON_RECURRING"
  | "NON_OPERATING"
  | "NORMALIZATION"
  | "OWNER_RELATED"
  | "PRO_FORMA";

export type AdjustmentStatus =
  | "CANDIDATE"
  | "PROPOSED"
  | "APPROVED"
  | "REJECTED";

// ── Adjustment Item ─────────────────────────────────────

export interface AdjustmentItemRead {
  id: string;
  qoe_calculation_id: string;
  deal_id: string;
  category: AdjustmentCategory;
  description: string;
  amount: string; // Decimal as string — NEVER number
  detection_method: string;
  confidence_score: string | null;
  source_account_code: string | null;
  source_account_name: string | null;
  source_entry_ids: string[] | null;
  status: AdjustmentStatus;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface AdjustmentItemCreate {
  category: AdjustmentCategory;
  description: string;
  amount: string;
  source_account_code?: string | null;
  source_account_name?: string | null;
}

export interface AdjustmentItemUpdate {
  category?: AdjustmentCategory;
  description?: string;
  amount?: string;
  status?: AdjustmentStatus;
  rejection_reason?: string;
}

export interface AdjustmentItemApprove {
  approved_by: string;
}

// ── QoE Calculation ─────────────────────────────────────

export interface QoECalculationRead {
  id: string;
  deal_id: string;
  snapshot_id: string;
  revenue: string;
  cogs: string;
  gross_profit: string;
  sga: string;
  depreciation_amortization: string;
  other_operating: string;
  operating_income: string;
  reported_ebitda: string;
  total_adjustments: string;
  adjusted_ebitda: string;
  balance_check_error: string;
  category_breakdown: Record<string, unknown>;
  engine_version: string;
  status: QoEStatus;
  adjustments: AdjustmentItemRead[];
  created_at: string;
  updated_at: string;
}

export interface QoERunRequest {
  snapshot_id: string;
}

// ── Bridge Summary ──────────────────────────────────────

export interface QoEBridgeSummary {
  reported_ebitda: string;
  adjustments: AdjustmentItemRead[];
  total_adjustments: string;
  adjusted_ebitda: string;
  balance_check_error: string;
  is_balanced: boolean;
}
