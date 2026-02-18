export type DDWorkstream =
  | "FINANCIAL"
  | "LEGAL"
  | "TAX"
  | "COMMERCIAL"
  | "IT"
  | "HR"
  | "ENVIRONMENTAL"
  | "INSURANCE"
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
