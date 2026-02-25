// ── RFI Status ────────────────────────────────────────

export type RFIStatus =
  | "DRAFT"
  | "SENT"
  | "PARTIALLY_RESPONDED"
  | "FULLY_RESPONDED"
  | "CLOSED"
  | "CANCELLED";

export type RFIItemStatus =
  | "PENDING"
  | "RESPONDED"
  | "CLARIFICATION_NEEDED"
  | "ACCEPTED"
  | "NOT_APPLICABLE";

export type RFIItemPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type RFICategory =
  | "GENERAL"
  | "FINANCIAL"
  | "TAX"
  | "LEGAL"
  | "OPERATIONAL"
  | "COMMERCIAL"
  | "HR"
  | "IT"
  | "ENVIRONMENTAL"
  | "INSURANCE"
  | "IP"
  | "REAL_ESTATE"
  | "VALUATION"
  | "OTHER";

export type RFISourceType =
  | "MANUAL"
  | "IM_CHECKLIST"
  | "FDD_CHECKLIST"
  | "DD_CHECKLIST"
  | "EXCEL_IMPORT"
  | "AI_SUGGESTED";

// ── RFI ───────────────────────────────────────────────

export interface RFI {
  id: string;
  transaction_id: string;
  round_number: number;
  title: string;
  description: string | null;
  status: RFIStatus;
  recipient_name: string | null;
  recipient_email: string | null;
  recipient_company: string | null;
  due_date: string | null;
  sent_at: string | null;
  closed_at: string | null;
  total_items: number;
  responded_items: number;
  accepted_items: number;
  created_by_email: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RFIDetail extends RFI {
  items: RFIItem[];
}

// ── RFI Item ──────────────────────────────────────────

export interface RFIChecklistMapping {
  id: string;
  rfi_item_id: string;
  target_module: string;
  target_checklist_id: string | null;
  target_item_id: string | null;
  target_field_key: string | null;
  synced: boolean;
  synced_at: string | null;
  synced_value: string | null;
}

export interface RFIItem {
  id: string;
  rfi_id: string;
  transaction_id: string;
  question_number: number;
  category: RFICategory;
  question: string;
  question_detail: string | null;
  priority: RFIItemPriority;
  response: string | null;
  response_documents: Record<string, unknown>[] | null;
  responded_at: string | null;
  responded_by: string | null;
  reviewer_comment: string | null;
  reviewer_email: string | null;
  status: RFIItemStatus;
  assignee_email: string | null;
  due_date: string | null;
  source_type: RFISourceType;
  source_ref_id: string | null;
  source_ref_key: string | null;
  vdr_document_ids: string[] | null;
  notes: string | null;
  follow_up_question: string | null;
  checklist_mappings: RFIChecklistMapping[];
  created_at: string;
  updated_at: string;
}

// ── Create / Update ───────────────────────────────────

export interface RFICreate {
  round_number?: number;
  title: string;
  description?: string;
  recipient_name?: string;
  recipient_email?: string;
  recipient_company?: string;
  due_date?: string;
  notes?: string;
}

export interface RFIUpdate {
  title?: string;
  description?: string;
  recipient_name?: string;
  recipient_email?: string;
  recipient_company?: string;
  due_date?: string;
  notes?: string;
  status?: RFIStatus;
}

export interface RFIItemCreate {
  category: RFICategory;
  question: string;
  question_detail?: string;
  priority?: RFIItemPriority;
  assignee_email?: string;
  due_date?: string;
  source_type?: RFISourceType;
  source_ref_id?: string;
  source_ref_key?: string;
  notes?: string;
}

export interface RFIItemUpdate {
  category?: RFICategory;
  question?: string;
  question_detail?: string;
  priority?: RFIItemPriority;
  assignee_email?: string;
  due_date?: string;
  status?: RFIItemStatus;
  notes?: string;
}

export interface RFIItemRespondInput {
  response: string;
  response_documents?: Record<string, unknown>[];
}

export interface RFIItemReviewInput {
  status: "ACCEPTED" | "CLARIFICATION_NEEDED";
  reviewer_comment?: string;
  follow_up_question?: string;
}

// ── Summary ───────────────────────────────────────────

export interface RFICategorySummary {
  category: RFICategory;
  total: number;
  responded: number;
  accepted: number;
  pending: number;
}

export interface RFISummary {
  total_rfis: number;
  total_items: number;
  responded_items: number;
  accepted_items: number;
  overall_response_pct: number;
  overdue_items: number;
  by_category: RFICategorySummary[];
}

export interface RFIAutoGenerateResult {
  rfi_id: string;
  items_created: number;
}

export interface RFIExcelImportResult {
  items_imported: number;
  items_updated: number;
  errors: string[];
}
