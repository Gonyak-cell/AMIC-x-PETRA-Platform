export type ClosingCategory = "REGULATORY" | "LEGAL" | "FINANCIAL" | "CORPORATE" | "CONDITION_PRECEDENT" | "FUND_FLOW" | "OTHER";

export type ClosingConditionStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "WAIVED" | "NOT_APPLICABLE";

export interface ClosingChecklistItem {
  id: string;
  transaction_id: string;
  category: ClosingCategory;
  title: string;
  description: string | null;
  status: ClosingConditionStatus;
  responsible_party: string | null;
  responsible_email: string | null;
  due_date: string | null;
  completed_date: string | null;
  document_url: string | null;
  notes: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ClosingChecklistCreate {
  category: ClosingCategory;
  title: string;
  description?: string;
  responsible_party?: string;
  responsible_email?: string;
  due_date?: string;
  document_url?: string;
  notes?: string;
  sort_order?: number;
}

export interface ClosingChecklistUpdate {
  category?: ClosingCategory;
  title?: string;
  description?: string;
  status?: ClosingConditionStatus;
  responsible_party?: string;
  responsible_email?: string;
  due_date?: string;
  completed_date?: string;
  document_url?: string;
  notes?: string;
  sort_order?: number;
}

export interface ClosingChecklistSummary {
  total: number;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
  completion_rate: number;
}
