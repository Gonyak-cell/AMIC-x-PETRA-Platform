// ── Checklist Types (VDR-based IM workflow) ──────────────────

export type ChecklistCategory =
  | "FINANCIAL"
  | "COMPANY"
  | "MARKET"
  | "DEAL"
  | "MANAGEMENT"
  | "SHAREHOLDERS";

export type ChecklistItemStatus =
  | "EXTRACTED"
  | "CONFIRMED"
  | "MODIFIED"
  | "MISSING"
  | "NOT_APPLICABLE";

export type FieldType =
  | "text"
  | "number"
  | "currency"
  | "percentage"
  | "date"
  | "list";

export type ChecklistStatusType =
  | "EXTRACTING"
  | "REVIEW"
  | "CONFIRMED"
  | "GENERATING"
  | "COMPLETED"
  | "FAILED";

export interface ChecklistItem {
  id: string;
  checklist_id: string;
  category: ChecklistCategory;
  field_key: string;
  field_label: string;
  field_type: FieldType;
  extracted_value: string | null;
  confirmed_value: string | null;
  unit: string | null;
  source_vdr_doc_id: string | null;
  source_vdr_doc_name: string | null;
  source_location: string | null;
  status: ChecklistItemStatus;
  confidence: number | null;
  sort_order: number;
  notes: string | null;
  is_required: boolean;
  fiscal_year: number | null;
  created_at: string;
  updated_at: string;
}

export interface Checklist {
  id: string;
  document_id: string;
  transaction_id: string | null;
  vdr_document_ids: string[];
  status: ChecklistStatusType;
  total_items: number;
  confirmed_items: number;
  missing_items: number;
  extraction_task_id: string | null;
  generation_task_id: string | null;
  created_at: string;
  updated_at: string;
  confirmed_at: string | null;
  items: ChecklistItem[];
}

export interface CategorySummary {
  category: string;
  total: number;
  confirmed: number;
  missing: number;
  completion_pct: number;
}

export interface ChecklistSummary {
  status: string;
  total_items: number;
  confirmed_items: number;
  missing_items: number;
  completion_pct: number;
  categories: CategorySummary[];
}

export interface CreateFromVdrRequest {
  transaction_id: string;
  vdr_document_ids: string[];
  company_name: string;
  project_name: string;
  im_style?: string;
  industry?: string;
}

export interface CreateFromVdrResponse {
  document_id: string;
  checklist_id: string;
  status: string;
  extraction_task_id: string | null;
  message: string;
}

// ── Constants ──────────────────────────────────────────────

export const CHECKLIST_CATEGORIES: {
  id: ChecklistCategory;
  label: string;
}[] = [
  { id: "FINANCIAL", label: "Financial" },
  { id: "COMPANY", label: "Company" },
  { id: "MARKET", label: "Market" },
  { id: "DEAL", label: "Deal" },
  { id: "MANAGEMENT", label: "Management" },
  { id: "SHAREHOLDERS", label: "Shareholders" },
];

export const CHECKLIST_CATEGORY_LABEL: Record<ChecklistCategory, string> = {
  FINANCIAL: "Financial",
  COMPANY: "Company",
  MARKET: "Market",
  DEAL: "Deal",
  MANAGEMENT: "Management",
  SHAREHOLDERS: "Shareholders",
};

export const CHECKLIST_STATUS_LABEL: Record<ChecklistStatusType, string> = {
  EXTRACTING: "Extracting",
  REVIEW: "Review",
  CONFIRMED: "Confirmed",
  GENERATING: "Generating",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

export const ITEM_STATUS_LABEL: Record<ChecklistItemStatus, string> = {
  EXTRACTED: "Extracted",
  CONFIRMED: "Confirmed",
  MODIFIED: "Modified",
  MISSING: "Missing",
  NOT_APPLICABLE: "N/A",
};

/** Statuses where the checklist is actively processing. */
export const CHECKLIST_IN_PROGRESS_STATUSES: ChecklistStatusType[] = [
  "EXTRACTING",
  "GENERATING",
];
