export type DDWorkstream =
  // FDD (재무실사)
  | "FDD_FINANCIAL_STATEMENTS"
  | "FDD_REVENUE"
  | "FDD_WORKING_CAPITAL"
  | "FDD_DEBT_CASH"
  | "FDD_PROJECTIONS"
  // LDD (법률실사)
  | "LDD_CORPORATE"
  | "LDD_PERMITS"
  | "LDD_CONTRACTS"
  | "LDD_ASSETS"
  | "LDD_LABOR"
  | "LDD_LITIGATION"
  | "LDD_IP"
  | "LDD_INSURANCE"
  | "LDD_ENVIRONMENT"
  // TDD (세무실사)
  | "TDD_CORPORATE_TAX"
  | "TDD_VAT"
  | "TDD_TRANSFER_PRICING"
  | "TDD_WITHHOLDING"
  | "TDD_TAX_INCENTIVES"
  // 기타
  | "OTHER";

export type DDChecklistStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "NOT_APPLICABLE";

export interface DDChecklistItem {
  id: string;
  transaction_id: string;
  workstream: DDWorkstream;
  title: string;
  description: string | null;
  assignee_email: string | null;
  status: DDChecklistStatus;
  due_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DDChecklistCreate {
  workstream: DDWorkstream;
  title: string;
  description?: string;
  assignee_email?: string;
  due_date?: string;
  notes?: string;
}

export interface DDChecklistUpdate {
  workstream?: DDWorkstream;
  title?: string;
  description?: string;
  assignee_email?: string;
  status?: DDChecklistStatus;
  due_date?: string;
  notes?: string;
}

export interface DDWorkstreamSummary {
  workstream: DDWorkstream;
  total: number;
  completed: number;
  in_progress: number;
  not_started: number;
}

export interface DDChecklistSummary {
  total: number;
  by_workstream: DDWorkstreamSummary[];
  overall_completion_pct: number;
}
