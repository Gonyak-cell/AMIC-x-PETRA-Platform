/** 계약서 자동 생성 타입 정의 */

// ── 변수 입력 유형 ────────────────────────────────────────────────────────
export type TemplateVariableInputType =
  | "TEXT"
  | "TEXTAREA"
  | "NUMBER"
  | "DATE"
  | "SELECT"
  | "BOOLEAN"
  | "CURRENCY"
  | "PERCENTAGE";

// ── 템플릿 ────────────────────────────────────────────────────────────────
export interface ContractTemplate {
  id: string;
  doc_type: string;
  name: string;
  description: string | null;
  version: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// ── 조항 ──────────────────────────────────────────────────────────────────
export interface ContractClause {
  id: string;
  clause_order: number;
  title: string;
  content: string;
  is_boilerplate: boolean;
  condition_expression: string | null;
}

// ── 변수 ──────────────────────────────────────────────────────────────────
export interface TemplateVariable {
  id: string;
  variable_key: string;
  input_type: TemplateVariableInputType;
  question_label: string;
  description: string | null;
  default_value: string | null;
  is_required: boolean;
  select_options: Record<string, string> | null;
  display_order: number;
  group_name: string | null;
  visible_condition: string | null;
}

// ── 템플릿 상세 ──────────────────────────────────────────────────────────
export interface ContractTemplateDetail {
  template: ContractTemplate;
  clauses: ContractClause[];
  variables: TemplateVariable[];
}

// ── 생성 요청/응답 ──────────────────────────────────────────────────────
export interface ContractGenerateRequest {
  template_id: string;
  title: string;
  variables: Record<string, unknown>;
  use_llm_smoothing: boolean;
}

export interface GenerationTiming {
  template_lookup: number;
  validation: number;
  assembly: number;
  html_build: number;
  llm_smoothing: number;
  total: number;
}

export interface ContractGenerationResult {
  legal_document_id: string;
  html: string;
  clauses_used: number;
  clauses_skipped: number;
  llm_smoothed: boolean;
  llm_cost_usd: number | null;
  updated_at: string;
  timing: GenerationTiming | null;
}

// ── DOCX 내보내기 ───────────────────────────────────────────────────────
export interface ContractExportRequest {
  html: string;
  title: string;
  legal_document_id?: string;
}

// ── HTML 저장 ────────────────────────────────────────────────────────────
export interface ContractSaveHtmlRequest {
  html: string;
  last_modified_at?: string | null;
}

export interface ContractSaveHtmlResponse {
  status: string;
  updated_at: string;
  html: string | null;
}

// ── 문서 유형 메타 ──────────────────────────────────────────────────────
export const CONTRACT_TYPE_META: Record<
  string,
  { label: string; labelKo: string; description: string; color: string }
> = {
  SPA: {
    label: "SPA",
    labelKo: "주식매매계약",
    description: "Share Purchase Agreement",
    color: "bg-info-light text-info",
  },
  SHA: {
    label: "SHA",
    labelKo: "주주간계약",
    description: "Shareholders' Agreement",
    color: "bg-violet-100 text-violet-700",
  },
  BTA: {
    label: "BTA",
    labelKo: "영업양수도계약",
    description: "Business Transfer Agreement",
    color: "bg-emerald-100 text-emerald-700",
  },
  SSA: {
    label: "SSA",
    labelKo: "신주인수계약",
    description: "Share Subscription Agreement",
    color: "bg-orange-100 text-orange-700",
  },
  MOU: {
    label: "MOU",
    labelKo: "양해각서",
    description: "Memorandum of Understanding",
    color: "bg-sky-100 text-sky-700",
  },
};
