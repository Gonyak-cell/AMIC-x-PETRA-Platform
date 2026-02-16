export type DealType = "COMPLETION_ACCOUNTS" | "LOCKED_BOX";
export type DealStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";
export type DefinitionStatus = "DRAFT" | "APPROVED" | "LOCKED";
export type SnapshotStatus = "RUNNING" | "SUCCESS" | "FAILED";
export type DealPhase = "MOU" | "VDR_SETUP" | "DATA_UPLOAD" | "ANALYSIS" | "REPORTING";

import type { IndustryId } from "@/types/industry";
/** @deprecated Use IndustryId from @/types/industry directly */
export type IndustryType = IndustryId;

export interface Deal {
  id: string;
  name: string;
  deal_type: DealType;
  base_currency: string;
  reference_date: string;
  period_start: string;
  period_end: string;
  status: DealStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  client_name: string | null;
  client_contact_name: string | null;
  client_contact_email: string | null;
  target_company_name: string | null;
  team_partner_id: string | null;
  team_manager_id: string | null;
  scope_qoe: boolean;
  scope_nwc: boolean;
  scope_debt: boolean;
  industry: IndustryType;
  current_phase: DealPhase;
}

export interface DealCreate {
  name: string;
  deal_type: DealType;
  base_currency: string;
  reference_date: string;
  period_start: string;
  period_end: string;
  client_name?: string;
  client_contact_name?: string;
  client_contact_email?: string;
  target_company_name?: string;
  team_partner_id?: string;
  team_manager_id?: string;
  scope_qoe?: boolean;
  scope_nwc?: boolean;
  scope_debt?: boolean;
  industry?: IndustryType;
}

export interface DefinitionData {
  cash: { include: string[]; exclude: string[] };
  debt: { include: string[]; exclude: string[] };
  debt_like: Array<Record<string, unknown>>;
  cash_like: Array<Record<string, unknown>>;
  nwc: { include: string[]; exclude: string[] };
  target_nwc: { method: string; value: number | null };
  lease_ifrs16: { include_in_debt: boolean };
}

export interface DealDefinition {
  id: string;
  deal_id: string;
  version: number;
  definition_data: DefinitionData;
  status: DefinitionStatus;
  approved_by: string | null;
  approved_at: string | null;
  hash: string;
  created_at: string;
  updated_at: string;
}

export interface DealSnapshot {
  id: string;
  deal_id: string;
  definition_version_id: string;
  engine_version: string;
  input_hash: string;
  result_hash: string | null;
  status: SnapshotStatus;
  created_at: string;
}

// ── Upload Types ────────────────────────────────────────

export type UploadType = "TB" | "GL" | "AR" | "AP" | "BANK" | "DEBT" | "LEASE";
export type IngestionStatus =
  | "PENDING"
  | "DETECTING"
  | "VALIDATING"
  | "INGESTING"
  | "COMPLETED"
  | "FAILED";
export type ValidationSeverity = "ERROR" | "WARNING";

export interface ValidationSummary {
  rows_ingested?: number;
  total_warnings?: number;
  total_errors?: number;
  [key: string]: unknown;
}

export interface UploadFile {
  id: string;
  deal_id: string;
  original_filename: string;
  file_hash: string;
  file_size_bytes: number;
  detected_type: UploadType | null;
  confirmed_type: UploadType | null;
  detection_confidence: number | null;
  status: IngestionStatus;
  total_rows: number | null;
  rows_processed: number | null;
  sheet_name: string | null;
  error_message: string | null;
  validation_summary: ValidationSummary | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface ValidationErrorItem {
  id: string;
  severity: ValidationSeverity;
  error_code: string;
  field_name: string | null;
  row_number: number | null;
  message: string;
  suggestion: string | null;
}

export interface UploadFileDetail extends UploadFile {
  validation_errors: ValidationErrorItem[];
}
