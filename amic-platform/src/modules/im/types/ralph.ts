/** IM Ralph Loop 타입 정의. */

export type RalphSessionStatus =
  | "PLANNING"
  | "GENERATING"
  | "VALIDATING"
  | "COMPLETED"
  | "FAILED"
  | "BUDGET_EXCEEDED";

export interface IMRalphSession {
  id: string;
  document_id: string;
  pass_number: 1 | 2;
  doc_type: string;
  status: RalphSessionStatus;
  total_iterations: number;
  total_cost_usd: number;
  final_score: number;
  section_scores: Record<string, number> | null;
  output_path: string | null;
  error_message: string | null;
  critical_flags: string[] | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface RalphProgressData {
  session_id: string;
  status: RalphSessionStatus;
  current_section: string | null;
  current_iteration: number;
  total_sections: number;
  scores: Record<string, number>;
  gate_results: GateResultSummary[];
}

export interface GateResultSummary {
  gate_name: string;
  verdict: string;
  weighted_score: number;
  issues: string[];
  suggestions: string[];
}

export const RALPH_ACTIVE_STATUSES: RalphSessionStatus[] = [
  "PLANNING",
  "GENERATING",
  "VALIDATING",
];
