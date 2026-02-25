export type ComplianceCategory =
  | "ANTITRUST"
  | "FOREIGN_INVESTMENT"
  | "SECURITIES"
  | "DATA_PRIVACY"
  | "ANTI_CORRUPTION"
  | "SANCTIONS"
  | "ENVIRONMENTAL"
  | "LABOR"
  | "TAX"
  | "PERMITS"
  | "OTHER";

export type ComplianceStatus =
  | "NOT_STARTED"
  | "IN_REVIEW"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "FLAGGED"
  | "NON_COMPLIANT"
  | "WAIVED";

export interface ComplianceItem {
  id: string;
  transaction_id: string;
  category: ComplianceCategory;
  requirement: string;
  description: string | null;
  jurisdiction: string | null;
  regulatory_body: string | null;
  assignee_email: string | null;
  status: ComplianceStatus;
  due_date: string | null;
  filing_reference: string | null;
  document_url: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComplianceItemCreate {
  category: ComplianceCategory;
  requirement: string;
  description?: string;
  jurisdiction?: string;
  regulatory_body?: string;
  assignee_email?: string;
  due_date?: string;
  filing_reference?: string;
  document_url?: string;
  notes?: string;
}

export interface ComplianceItemUpdate {
  category?: ComplianceCategory;
  requirement?: string;
  description?: string;
  jurisdiction?: string;
  regulatory_body?: string;
  assignee_email?: string;
  status?: ComplianceStatus;
  due_date?: string;
  filing_reference?: string;
  document_url?: string;
  notes?: string;
}

export interface ComplianceCategorySummary {
  category: ComplianceCategory;
  total: number;
  approved: number;
  flagged: number;
  pending: number;
}

export interface ComplianceSummary {
  total: number;
  by_category: ComplianceCategorySummary[];
  by_status: Record<string, number>;
  compliance_rate: number;
  flagged_count: number;
  overdue_count: number;
}
