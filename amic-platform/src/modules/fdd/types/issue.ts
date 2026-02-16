// ── Enums ────────────────────────────────────────────────

export type IssueCategory =
  | "ANOMALY"
  | "DATA_QUALITY"
  | "MAPPING"
  | "CALCULATION"
  | "AI_SUGGESTION";

export type IssueSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type IssueStatus =
  | "OPEN"
  | "UNDER_REVIEW"
  | "RESOLVED"
  | "FALSE_POSITIVE"
  | "ACKNOWLEDGED";

// ── Issue ────────────────────────────────────────────────

export interface IssueRead {
  id: string;
  deal_id: string;
  snapshot_id: string | null;
  category: IssueCategory;
  severity: IssueSeverity;
  status: IssueStatus;
  title: string;
  description: string;
  risk_score: string | null; // Decimal as string
  source_type: string | null;
  source_id: string | null;
  source_detail: Record<string, unknown> | null;
  detection_method: string;
  detection_factors: Record<string, unknown>[] | null;
  engine_version: string | null;
  resolution_note: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IssueCreate {
  category: IssueCategory;
  severity: IssueSeverity;
  title: string;
  description: string;
  source_type?: string | null;
  source_id?: string | null;
  source_detail?: Record<string, unknown> | null;
  detection_method?: string;
}

export interface IssueUpdate {
  status: IssueStatus;
  resolution_note?: string | null;
  resolved_by?: string | null;
}

// ── Issue List Response ──────────────────────────────────

export interface IssueListResponse {
  items: IssueRead[];
  total: number;
  limit: number;
  offset: number;
}

// ── Issue Summary ────────────────────────────────────────

export interface IssueSummary {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
}

// ── Anomaly Detection ────────────────────────────────────

export interface AnomalyDetectionRequest {
  snapshot_id?: string | null;
  threshold?: string; // Decimal as string
}

export interface AnomalyDetectionResponse {
  detected_count: number;
  issues_created: number;
  engine_version: string;
  threshold_used: string;
}
