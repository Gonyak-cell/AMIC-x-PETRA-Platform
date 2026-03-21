// ── Financial Model Types ──────────────────────────────────

export type FinancialModelType =
  | "DCF"
  | "LBO"
  | "COMPS"
  | "TRANSACTION_COMPS"
  | "PROJECTION"
  | "FULL";

export type FinancialModelStatus =
  | "DRAFT"
  | "GENERATING"
  | "PENDING_REVIEW"
  | "FINALIZING"
  | "READY"
  | "FAILED";

export type FMChecklistStatus =
  | "GENERATING"
  | "PENDING_REVIEW"
  | "REVIEWED" // DB enum 호환용 — 백엔드 서비스 미전환, FE 렌더링은 준비됨
  | "FINALIZED";

export type FMChecklistItemStatus =
  | "AUTO_GENERATED"
  | "CONFIRMED"
  | "CORRECTED"
  | "FLAGGED"
  | "NOT_APPLICABLE";

export type FMChecklistSeverity = "HIGH" | "MEDIUM" | "LOW" | "INFO";

export type FMChecklistCategory =
  | "REVENUE_FORECAST"
  | "GROWTH_ASSUMPTIONS"
  | "VOLUME_PRICE_MIX"
  | "COGS_FORECAST"
  | "SGA_FORECAST"
  | "DEPRECIATION_AMORT"
  | "CAPEX_FORECAST"
  | "NWC_ASSUMPTIONS"
  | "FCF_DERIVATION"
  | "FM_DEBT_SCHEDULE"
  | "WACC_COMPONENTS"
  | "TAX_RATE"
  | "DCF_PARAMETERS"
  | "TRADING_MULTIPLES"
  | "TRANSACTION_MULTIPLES"
  | "BASE_SCENARIO"
  | "UPSIDE_SCENARIO"
  | "DOWNSIDE_SCENARIO"
  | "SENSITIVITY_MATRIX";

// ── Interfaces ──────────────────────────────────────────────

export interface FinancialModelSourceRoutingDocument {
  document_id: string;
  original_name: string;
  folder_category: string;
  ddrl_sections: string[];
  primary_workstream: string;
  workstream_tags: string[];
  confidence: number;
  requires_manual_review: boolean;
  reasons: string[];
  include_for_financial_model?: boolean;
}

export interface FinancialModelSourceRouting {
  version: string;
  summary: {
    total_documents: number;
    included_for_financial_model?: number;
    excluded_from_financial_model?: number;
    manual_review_documents: number;
    by_primary_workstream: Record<string, number>;
    target_workstreams?: string[];
  };
  documents: FinancialModelSourceRoutingDocument[];
}

export interface FinancialModelParameters extends Record<string, unknown> {
  source_routing?: FinancialModelSourceRouting;
  financial_model_workstreams?: string[];
  seeded_checklist_items?: number;
}

export interface FMChecklistSourceMetadata extends Record<string, unknown> {
  workstream_tags?: string[];
  primary_workstream?: string;
  routing_confidence?: number;
  requires_manual_review?: boolean;
  routing_reasons?: string[];
  chunk_id?: string;
}

export interface FinancialModel {
  id: string;
  transaction_id: string;
  model_type: FinancialModelType;
  title: string;
  version: number;
  status: FinancialModelStatus;
  error_message: string | null;
  parameters: FinancialModelParameters | null;
  vdr_document_ids: string[] | null;
  file_path: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  ralph_session_id: string | null;
  ralph_score: number | null;
  quality_status: string | null;
  quality_report: Record<string, unknown> | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialModelCreate {
  model_type: FinancialModelType;
  title: string;
  vdr_document_ids?: string[];
  parameters?: FinancialModelParameters;
  enable_ralph_loop?: boolean;
  ralph_max_iterations?: number;
  ralph_max_cost_usd?: number;
}

export interface FMChecklistItem {
  id: string;
  checklist_id: string;
  category: FMChecklistCategory;
  order_index: number;
  title: string;
  description: string;
  auto_finding: string | null;
  auto_value: string | null;
  user_correction: string | null;
  user_value: string | null;
  status: FMChecklistItemStatus;
  severity: FMChecklistSeverity | null;
  unit: string | null;
  field_type: string | null;
  confidence: number | null;
  source_vdr_doc_id: string | null;
  source_vdr_doc_name: string | null;
  source_location: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  extra_metadata: FMChecklistSourceMetadata | null;
  created_at: string;
  updated_at: string;
}

export interface FMChecklist {
  id: string;
  financial_model_id: string;
  version: number;
  status: FMChecklistStatus;
  notes: string | null;
  finalized_at: string | null;
  finalized_by: string | null;
  created_at: string;
  updated_at: string;
  items: FMChecklistItem[];
  total_items: number;
  confirmed_count: number;
  corrected_count: number;
  flagged_count: number;
  pending_count: number;
  not_applicable_count: number;
}

export interface FMChecklistItemUpdate {
  status: FMChecklistItemStatus;
  user_correction?: string | null;
  user_value?: string | null;
}

export interface FMChecklistBulkItem {
  item_id: string;
  status: FMChecklistItemStatus;
  user_correction?: string | null;
  user_value?: string | null;
}

// ── Constants ──────────────────────────────────────────────

export const FM_MODEL_TYPE_LABELS: Record<FinancialModelType, string> = {
  DCF: "DCF Valuation",
  LBO: "LBO Analysis",
  COMPS: "비교기업 분석",
  TRANSACTION_COMPS: "선례거래 분석",
  PROJECTION: "사업계획 프로젝션",
  FULL: "Full Financial Model",
};

export const FM_STATUS_LABELS: Record<FinancialModelStatus, string> = {
  DRAFT: "초안",
  GENERATING: "생성 중",
  PENDING_REVIEW: "리뷰 대기",
  FINALIZING: "최종 생성 중",
  READY: "완료",
  FAILED: "실패",
};

export const FM_STATUS_COLORS: Record<FinancialModelStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  GENERATING: "bg-yellow-100 text-yellow-700",
  PENDING_REVIEW: "bg-blue-100 text-blue-700",
  FINALIZING: "bg-indigo-100 text-indigo-700",
  READY: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

export const FM_ITEM_STATUS_LABELS: Record<FMChecklistItemStatus, string> = {
  AUTO_GENERATED: "자동 추출",
  CONFIRMED: "확인",
  CORRECTED: "수정",
  FLAGGED: "플래그",
  NOT_APPLICABLE: "해당 없음",
};

export const FM_ITEM_STATUS_COLORS: Record<FMChecklistItemStatus, string> = {
  AUTO_GENERATED: "bg-gray-100 text-gray-600",
  CONFIRMED: "bg-green-100 text-green-700",
  CORRECTED: "bg-yellow-100 text-yellow-700",
  FLAGGED: "bg-red-100 text-red-700",
  NOT_APPLICABLE: "bg-gray-50 text-gray-400",
};

export const FM_SEVERITY_COLORS: Record<FMChecklistSeverity, string> = {
  HIGH: "text-red-600",
  MEDIUM: "text-yellow-600",
  LOW: "text-green-600",
  INFO: "text-gray-400",
};

export const FM_CATEGORY_GROUPS: Record<string, FMChecklistCategory[]> = {
  "Revenue & Growth": [
    "REVENUE_FORECAST",
    "GROWTH_ASSUMPTIONS",
    "VOLUME_PRICE_MIX",
  ],
  "Cost Structure": [
    "COGS_FORECAST",
    "SGA_FORECAST",
    "DEPRECIATION_AMORT",
    "CAPEX_FORECAST",
  ],
  "Working Capital & Cash Flow": ["NWC_ASSUMPTIONS", "FCF_DERIVATION"],
  "Capital Structure & WACC": [
    "FM_DEBT_SCHEDULE",
    "WACC_COMPONENTS",
    "TAX_RATE",
  ],
  Valuation: ["DCF_PARAMETERS", "TRADING_MULTIPLES", "TRANSACTION_MULTIPLES"],
  "Scenarios & Sensitivity": [
    "BASE_SCENARIO",
    "UPSIDE_SCENARIO",
    "DOWNSIDE_SCENARIO",
    "SENSITIVITY_MATRIX",
  ],
};

export const FM_CATEGORY_LABELS: Record<FMChecklistCategory, string> = {
  REVENUE_FORECAST: "매출 추정",
  GROWTH_ASSUMPTIONS: "성장률 가정",
  VOLUME_PRICE_MIX: "물량/단가/믹스",
  COGS_FORECAST: "매출원가 추정",
  SGA_FORECAST: "판관비 추정",
  DEPRECIATION_AMORT: "감가상각",
  CAPEX_FORECAST: "CAPEX 가정",
  NWC_ASSUMPTIONS: "운전자본 가정",
  FCF_DERIVATION: "FCF 도출",
  FM_DEBT_SCHEDULE: "차입금 구조",
  WACC_COMPONENTS: "WACC 구성요소",
  TAX_RATE: "유효세율",
  DCF_PARAMETERS: "DCF 파라미터",
  TRADING_MULTIPLES: "비교기업 멀티플",
  TRANSACTION_MULTIPLES: "선례거래 멀티플",
  BASE_SCENARIO: "Base Case",
  UPSIDE_SCENARIO: "Upside Case",
  DOWNSIDE_SCENARIO: "Downside Case",
  SENSITIVITY_MATRIX: "민감도 분석",
};

/** 재무모델이 활발히 처리 중인 상태 (폴링 대상). */
export const FM_IN_PROGRESS_STATUSES: FinancialModelStatus[] = [
  "GENERATING",
  "FINALIZING",
];

/** 품질 상태 Tailwind 색상 */
export const FM_QUALITY_STATUS_COLORS: Record<string, string> = {
  PASS: "bg-green-100 text-green-700",
  CONDITIONAL: "bg-yellow-100 text-yellow-700",
  FAIL: "bg-red-100 text-red-700",
  SKIPPED: "bg-gray-100 text-gray-500",
};

/** 품질 상태 한국어 라벨 */
export const FM_QUALITY_STATUS_LABELS: Record<string, string> = {
  PASS: "통과",
  CONDITIONAL: "조건부",
  FAIL: "미통과",
  SKIPPED: "미검증",
};
