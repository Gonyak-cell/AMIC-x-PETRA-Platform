export type PermitFilingType =
  | "CHANGE_NOTIFICATION"
  | "CHANGE_APPROVAL"
  | "NEW_REGISTRATION"
  | "RENEWAL";

export type PermitTimingType = "PRE_FILING" | "POST_FILING" | "BOTH";

export type PermitAnalysisStatus =
  | "PENDING"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED"
  | "MANUALLY_REVIEWED";

export type PermitRequirementStatus =
  | "IDENTIFIED"
  | "DOCUMENTS_PREPARING"
  | "FILED"
  | "APPROVED"
  | "NOT_APPLICABLE";

export interface ExistingPermit {
  name: string;
  issuer: string;
  reg_number?: string;
}

export interface RequiredDocument {
  name: string;
  description?: string;
}

export interface PermitAnalysis {
  id: string;
  transaction_id: string;
  status: PermitAnalysisStatus;
  business_types: string[] | null;
  existing_permits: ExistingPermit[] | null;
  analysis_method: string | null;
  llm_cost_usd: number | null;
  analysis_notes: string | null;
  analyzed_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface PermitRequirement {
  id: string;
  analysis_id: string;
  transaction_id: string;
  permit_name: string;
  regulatory_body: string;
  legal_basis: string | null;
  filing_type: PermitFilingType;
  timing_type: PermitTimingType;
  pre_filing_deadline_days: number | null;
  post_filing_deadline_days: number | null;
  calculated_deadline: string | null;
  required_documents: RequiredDocument[] | null;
  status: PermitRequirementStatus;
  source: string;
  confidence: number | null;
  compliance_item_id: string | null;
  notes: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface PermitAnalyzeRequest {
  business_types: string[];
  existing_permits: ExistingPermit[];
}

export interface PermitRequirementUpdate {
  status?: PermitRequirementStatus;
  notes?: string;
}

export interface IndustryOption {
  code: string;
  label: string;
  sub_categories: string[] | null;
}
