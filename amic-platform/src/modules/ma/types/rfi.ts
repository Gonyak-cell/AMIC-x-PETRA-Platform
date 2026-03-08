// ── RFI V2 Types — 질의 원장 + 스레드 이력 기반 ──────────

// ── Enums ────────────────────────────────────────────────

export type RFIItemStatusV2 =
  | "OPEN"
  | "ANSWERED"
  | "CLARIFICATION_NEEDED"
  | "CLOSED";

export type RFICategoryV2 =
  | "FINANCIAL"
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
  | "CORPORATE"
  | "TAX"
  | "OTHER";

export type RFIPriority = "HIGH" | "MEDIUM" | "LOW";

export type RFIAuthorRole = "ADVISOR" | "TARGET";

// ── Thread (답변/추가질의 — insert-only) ─────────────────

export interface RFIThread {
  id: string;
  item_id: string;
  round_num: number;
  author_email: string;
  author_role: RFIAuthorRole;
  content_text: string;
  is_published: boolean;
  created_at: string;
}

// ── Attachment (증빙 자료) ───────────────────────────────

export interface RFIAttachment {
  id: string;
  thread_id: string | null;
  item_id: string | null;
  transaction_id: string;
  vdr_index: string | null;
  file_name: string;
  file_url: string;
  is_mapped: boolean;
  created_at: string;
}

// ── RFI Item (질의 원장) ────────────────────────────────

export interface RFIItemV2 {
  id: string;
  transaction_id: string;
  item_number: string;
  category: RFICategoryV2;
  priority: RFIPriority;
  target_doc: string | null;
  question_text: string;
  current_status: RFIItemStatusV2;
  internal_memo: string | null;
  report_section_tag: string | null;
  assignee_email: string | null;
  due_date: string | null;
  created_by_email: string | null;
  version: number;
  is_deleted: boolean;
  created_at: string;
  updated_at: string | null;
  threads: RFIThread[];
  attachments: RFIAttachment[];
}

export interface RFIItemListOut {
  id: string;
  transaction_id: string;
  item_number: string;
  category: RFICategoryV2;
  priority: RFIPriority;
  target_doc: string | null;
  question_text: string;
  current_status: RFIItemStatusV2;
  report_section_tag: string | null;
  assignee_email: string | null;
  due_date: string | null;
  version: number;
  created_at: string;
  updated_at: string | null;
  thread_count: number;
  attachment_count: number;
}

// ── Create / Update ─────────────────────────────────────

export interface RFIItemCreate {
  category: RFICategoryV2;
  question_text: string;
  priority?: RFIPriority;
  target_doc?: string;
  assignee_email?: string;
  due_date?: string;
  internal_memo?: string;
  report_section_tag?: string;
}

export interface RFIItemUpdate {
  category?: RFICategoryV2;
  question_text?: string;
  priority?: RFIPriority;
  target_doc?: string;
  assignee_email?: string;
  due_date?: string;
  internal_memo?: string;
  report_section_tag?: string;
  current_status?: RFIItemStatusV2;
  version: number;
}

export interface RFIItemBatchCreate {
  items: RFIItemCreate[];
}

export interface RFIThreadCreate {
  content_text: string;
  is_published?: boolean;
}

export interface RFIAttachmentMapInput {
  item_id?: string;
  thread_id?: string;
}

// ── Dashboard ───────────────────────────────────────────

export interface RFICategoryBreakdown {
  category: RFICategoryV2;
  total: number;
  open: number;
  answered: number;
  closed: number;
  clarification_needed: number;
  response_pct: number;
}

export interface RFIDashboardSummary {
  total_items: number;
  status_counts: Partial<Record<RFIItemStatusV2, number>>;
  category_breakdown: RFICategoryBreakdown[];
  aging_items: RFIItemListOut[];
}

// ── Excel ───────────────────────────────────────────────

export interface RFIExcelImportResult {
  items_updated: number;
  threads_created: number;
  files_matched: number;
  files_unmatched: number;
  errors: Array<Record<string, string | number>>;
  conflicts: Array<Record<string, string | number>>;
}

// ── Report Bridge ───────────────────────────────────────

export interface RFIVerifiedFact {
  original_question: string;
  target_company_answers: string[];
  referenced_vdr_files: string[];
}

export interface RFIReportPayload {
  report_section: string;
  verified_facts: RFIVerifiedFact[];
}

// ── AI Generate ─────────────────────────────────────────

export interface RFIAutoGenerateRequest {
  industry: string;
  deal_purpose: string;
  focus_areas: string[];
  additional_context?: string;
}

export interface RFIAutoGenerateResult {
  items_created: number;
  cost_usd: number;
  model_used: string;
}
