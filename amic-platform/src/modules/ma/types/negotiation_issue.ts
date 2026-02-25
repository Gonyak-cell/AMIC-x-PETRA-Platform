// 협상 이견 추적 타입

export type NegotiationIssueStatus = "OPEN" | "IN_PROGRESS" | "AGREED" | "DEFERRED" | "DEADLOCKED";
export type NegotiationIssuePriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface NegotiationIssue {
  id: string;
  transaction_id: string;
  meeting_id: string | null;
  title: string;
  clause_reference: string | null;
  category: string | null;
  our_position: string | null;
  counterpart_position: string | null;
  legal_review: string | null;
  ai_suggestion: string | null;
  ai_suggestion_rationale: string | null;
  status: NegotiationIssueStatus;
  priority: NegotiationIssuePriority;
  resolution: string | null;
  resolved_at: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface NegotiationIssueCreate {
  meeting_id?: string;
  title: string;
  clause_reference?: string;
  category?: string;
  our_position?: string;
  counterpart_position?: string;
  legal_review?: string;
  status?: NegotiationIssueStatus;
  priority?: NegotiationIssuePriority;
}

export interface NegotiationIssueUpdate {
  meeting_id?: string;
  title?: string;
  clause_reference?: string;
  category?: string;
  our_position?: string;
  counterpart_position?: string;
  legal_review?: string;
  status?: NegotiationIssueStatus;
  priority?: NegotiationIssuePriority;
  resolution?: string;
  resolved_at?: string;
}

export interface NegotiationIssueListResponse {
  items: NegotiationIssue[];
  total: number;
}

export interface AIClauseSuggestionResponse {
  suggested_text: string;
  rationale: string;
  confidence: number;
}
