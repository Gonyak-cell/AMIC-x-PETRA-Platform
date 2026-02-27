// 협상 이견 추적 타입

export type NegotiationIssueStatus = "OPEN" | "IN_PROGRESS" | "AGREED" | "DEFERRED" | "DEADLOCKED";
export type NegotiationIssuePriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type IssueDecisionStatus = "PENDING" | "CONSIDER_ACCEPTING" | "CANNOT_ACCEPT";

export interface NegotiationIssue {
  id: string;
  transaction_id: string;
  meeting_id: string | null;
  contract_id: string | null;
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
  decision_status: IssueDecisionStatus;
  resolution: string | null;
  resolved_at: string | null;
  linked_issue_ids: string[] | null;
  markup_version_number: number | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface NegotiationIssueCreate {
  meeting_id?: string;
  contract_id?: string;
  title: string;
  clause_reference?: string;
  category?: string;
  our_position?: string;
  counterpart_position?: string;
  legal_review?: string;
  status?: NegotiationIssueStatus;
  priority?: NegotiationIssuePriority;
  decision_status?: IssueDecisionStatus;
  linked_issue_ids?: string[];
  markup_version_number?: number;
}

export interface NegotiationIssueUpdate {
  meeting_id?: string;
  contract_id?: string;
  title?: string;
  clause_reference?: string;
  category?: string;
  our_position?: string;
  counterpart_position?: string;
  legal_review?: string;
  status?: NegotiationIssueStatus;
  priority?: NegotiationIssuePriority;
  decision_status?: IssueDecisionStatus;
  resolution?: string;
  resolved_at?: string;
  linked_issue_ids?: string[];
  markup_version_number?: number;
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
