// ── Enums ────────────────────────────────────────────────

export type MappingConfidence = "HIGH" | "MEDIUM" | "LOW" | "UNMAPPED";
export type MappingStatus = "PROPOSED" | "APPROVED" | "REJECTED" | "MANUAL";
export type TieOutStatus = "PASS" | "FAIL" | "WARNING";
export type FinancialStatement = "IS" | "BS";
export type LineItemCategory =
  | "REVENUE"
  | "COGS"
  | "SGA"
  | "OTHER_OPERATING_INCOME"
  | "DEPRECIATION_AMORTIZATION"
  | "NON_OPERATING"
  | "INTEREST_EXPENSE"
  | "INTEREST_INCOME"
  | "TAX_EXPENSE"
  | "CASH"
  | "AR"
  | "INVENTORY"
  | "OTHER_CURRENT_ASSETS"
  | "PPE"
  | "INTANGIBLES"
  | "OTHER_NONCURRENT_ASSETS"
  | "AP"
  | "ACCRUALS"
  | "OTHER_CURRENT_LIABILITIES"
  | "DEBT"
  | "LEASE_LIABILITIES"
  | "OTHER_NONCURRENT_LIABILITIES"
  | "EQUITY";

// ── Standard Line Item ───────────────────────────────────

export interface StandardLineItem {
  id: string;
  code: string;
  name_en: string;
  name_ko: string;
  category: LineItemCategory;
  statement_type: FinancialStatement;
  display_order: number;
  parent_code: string | null;
  is_subtotal: boolean;
  keywords: string[] | null;
  created_at: string;
}

// ── Account Mapping ──────────────────────────────────────

export interface AccountMappingRead {
  id: string;
  deal_id: string;
  source_account_code: string;
  source_account_name: string;
  target_line_item_code: string;
  confidence: MappingConfidence;
  status: MappingStatus;
  match_score: string | null;
  algorithm: string | null;
  affected_amount: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountMappingCreate {
  source_account_code: string;
  source_account_name: string;
  target_line_item_code: string;
  confidence: MappingConfidence;
  status?: MappingStatus;
  match_score?: string | null;
  algorithm?: string | null;
  affected_amount: string;
}

export interface MappingBulkCreate {
  mappings: AccountMappingCreate[];
}

export interface AccountMappingUpdate {
  target_line_item_code?: string;
  status?: MappingStatus;
  rejection_reason?: string;
}

export interface AccountMappingApprove {
  approved_by: string;
}

// ── Mapping Suggestion ───────────────────────────────────

export interface MappingSuggestion {
  source_account_code: string;
  source_account_name: string;
  suggested_target_code: string;
  suggested_target_name_en: string;
  suggested_target_name_ko: string;
  confidence: MappingConfidence;
  match_score: string;
  algorithm: string;
  affected_amount: string;
}

// ── Tie-out ──────────────────────────────────────────────

export interface TieOutResultRead {
  id: string;
  deal_id: string;
  snapshot_id: string;
  statement_type: FinancialStatement;
  status: TieOutStatus;
  tb_total: string;
  reconstructed_total: string;
  variance: string;
  variance_percentage: string;
  unmapped_account_count: number;
  unmapped_total: string;
  top_discrepancies: Array<Record<string, string>> | null;
  created_at: string;
}

export interface TieOutRun {
  snapshot_id: string;
}

// ── Evidence Missing Detection ───────────────────────────

export interface MissingEvidenceItem {
  target_type: string;
  target_id: string;
  target_label: string;
  reason: string;
}

export interface DetectionResult {
  deal_id: string;
  total_targets_checked: number;
  missing_count: number;
  coverage_percentage: number;
  missing: MissingEvidenceItem[];
}
