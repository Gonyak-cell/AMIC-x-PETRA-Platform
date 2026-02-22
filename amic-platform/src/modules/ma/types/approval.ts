export type ApprovalType =
  | "PHASE_ADVANCE"
  | "STATUS_CHANGE"
  | "CONTRACT_SIGN"
  | "DEAL_TERMS";

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface ApproverEntry {
  email: string;
  role: string;
  status: string;
  comment: string | null;
  decided_at: string | null;
}

export interface ApprovalRequest {
  id: string;
  transaction_id: string;
  requester_email: string;
  approval_type: ApprovalType;
  title: string;
  description: string | null;
  status: ApprovalStatus;
  approvers: ApproverEntry[];
  deadline: string | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalCreate {
  approval_type: ApprovalType;
  title: string;
  description?: string;
  approvers: Omit<ApproverEntry, "status" | "comment" | "decided_at">[];
  deadline?: string;
  related_entity_type?: string;
  related_entity_id?: string;
}

export interface ApprovalDecision {
  email: string;
  decision: "APPROVED" | "REJECTED";
  comment?: string;
}

export interface ApprovalListResponse {
  items: ApprovalRequest[];
  total: number;
}

export interface ApprovalSummary {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}
