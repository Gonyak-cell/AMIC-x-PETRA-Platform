export type PMICategory =
  | "INTEGRATION_PLAN"
  | "DAY_ONE"
  | "FIRST_100_DAYS"
  | "SYNERGY"
  | "CULTURE"
  | "IT_SYSTEMS"
  | "HR"
  | "COMMUNICATION"
  | "OTHER";

export type PMITaskStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "BLOCKED"
  | "DEFERRED";

export type PMIPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface PMITask {
  id: string;
  transaction_id: string;
  category: PMICategory;
  title: string;
  description: string | null;
  status: PMITaskStatus;
  priority: PMIPriority;
  assignee_name: string | null;
  assignee_email: string | null;
  start_date: string | null;
  due_date: string | null;
  completed_date: string | null;
  dependency_ids: string[] | null;
  notes: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface PMITaskCreate {
  category: PMICategory;
  title: string;
  description?: string | null;
  priority?: PMIPriority;
  assignee_name?: string | null;
  assignee_email?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  dependency_ids?: string[] | null;
  notes?: string | null;
  sort_order?: number;
}

export interface PMITaskUpdate {
  category?: PMICategory;
  title?: string;
  description?: string | null;
  status?: PMITaskStatus;
  priority?: PMIPriority;
  assignee_name?: string | null;
  assignee_email?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  completed_date?: string | null;
  dependency_ids?: string[] | null;
  notes?: string | null;
  sort_order?: number;
}

export interface PMISummary {
  total: number;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  completion_rate: number;
}
