export type MilestoneType =
  | "PHASE_TRANSITION"
  | "STATUS_CHANGE"
  | "DOCUMENT_SIGNED"
  | "MEETING"
  | "DEADLINE"
  | "BUYER_UPDATE"
  | "SERVICE_LINKED"
  | "CUSTOM";

export interface Milestone {
  id: string;
  transaction_id: string;
  event_type: MilestoneType;
  title: string;
  description: string | null;
  event_date: string;
  is_auto_generated: boolean;
  created_by: string | null;
  created_at: string;
}

export interface MilestoneCreate {
  event_type: MilestoneType;
  title: string;
  description?: string;
  event_date: string;
}

export interface TimelineEvent {
  id: string;
  transaction_id: string;
  event_type: MilestoneType;
  title: string;
  description: string | null;
  event_date: string;
  is_auto_generated: boolean;
  created_by: string | null;
  created_at: string;
}

export interface TimelineResponse {
  items: TimelineEvent[];
  total: number;
}

// ── Gantt Timeline ────────────────────────────────────

export interface GanttPhaseBar {
  phase: string;
  label: string;
  start_date: string | null;
  end_date: string | null;
  status: "completed" | "active" | "upcoming";
  order: number;
}

export interface GanttMilestone {
  label: string;
  date: string;
  type: string;
}

export interface GanttResponse {
  phases: GanttPhaseBar[];
  milestones: GanttMilestone[];
  target_close_date: string | null;
  deal_start_date: string;
}
