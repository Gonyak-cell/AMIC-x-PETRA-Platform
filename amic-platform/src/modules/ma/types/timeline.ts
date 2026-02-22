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
