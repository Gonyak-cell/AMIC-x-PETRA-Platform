/** SPA 계약서 LLM 역분석 타입 정의 */

import type { TemplateVariableInputType } from "./contract_generation";

// ── 계약서 유형 ─────────────────────────────────────────────────────────────

export const DOC_TYPES = ["SPA", "SHA", "BTA", "SSA", "MOU"] as const;
export type DocType = (typeof DOC_TYPES)[number];

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  SPA: "주식매매계약 (SPA)",
  SHA: "주주간계약 (SHA)",
  BTA: "영업양수도계약 (BTA)",
  SSA: "신주인수계약 (SSA)",
  MOU: "양해각서 (MOU)",
};

// ── 확장 ENUM 상수 ──────────────────────────────────────────────────────────

export const DEAL_STRUCTURES = [
  "PURE_SHARE_TRANSFER",
  "CARVE_OUT",
  "WITH_NEW_SHARES",
  "OTHER_STRUCTURE",
] as const;
export type DealStructure = (typeof DEAL_STRUCTURES)[number];

export const DEAL_STRUCTURE_LABELS: Record<DealStructure, string> = {
  PURE_SHARE_TRANSFER: "단순 주식 양수도",
  CARVE_OUT: "물적분할 + 양수도",
  WITH_NEW_SHARES: "유상증자 동반",
  OTHER_STRUCTURE: "기타 구조",
};

export const INDUSTRY_TYPES = [
  "MANUFACTURING",
  "SOFTWARE",
  "FRANCHISE",
  "GENERAL",
  "OTHER_INDUSTRY",
] as const;
export type IndustryType = (typeof INDUSTRY_TYPES)[number];

export const INDUSTRY_TYPE_LABELS: Record<IndustryType, string> = {
  MANUFACTURING: "제조업",
  SOFTWARE: "소프트웨어/IT",
  FRANCHISE: "프랜차이즈",
  GENERAL: "일반",
  OTHER_INDUSTRY: "기타",
};

// ── Step 1: 변수 추출 ──────────────────────────────────────────────────────

export interface ExtractedVariable {
  variable_key: string;
  input_type: TemplateVariableInputType;
  question_label: string;
  description: string | null;
  extracted_value: string | null;
  default_value: string | null;
  is_required: boolean;
  select_options: Record<string, string> | null;
  display_order: number;
  group_name: string | null;
  visible_condition: string | null;
  confidence: number;
}

export interface DiscoveredBoolean {
  variable_key: string;
  question_label: string;
  detected_in_clause: string | null;
}

export interface SpaStep1Request {
  spa_text: string;
  language_hint?: "ko" | "en" | null;
}

export interface SpaStep1Response {
  session_id: string;
  variables: ExtractedVariable[];
  deal_structure: DealStructure;
  industry_type: IndustryType;
  detected_doc_type: DocType;
  discovered_booleans: DiscoveredBoolean[];
  llm_cost_usd: number | null;
  model_used: string | null;
}

// ── Step 2: 조항 분해 ──────────────────────────────────────────────────────

export interface AnalyzedClause {
  clause_order: number;
  title: string;
  content: string;
  original_content: string;
  is_boilerplate: boolean;
  condition_expression: string | null;
  confidence: number;
}

export interface SpaStep2Request {
  session_id: string;
  spa_text?: string;
  variables: ExtractedVariable[];
  deal_structure: DealStructure;
  industry_type: IndustryType;
}

export interface SpaStep2Response {
  session_id: string;
  clauses: AnalyzedClause[];
  llm_cost_usd: number | null;
  model_used: string | null;
}

// ── Step 3: 템플릿 생성 ────────────────────────────────────────────────────

export interface SpaStep3Request {
  session_id: string;
  template_name: string;
  template_description?: string | null;
  doc_type?: DocType;
  variables: ExtractedVariable[];
  clauses: AnalyzedClause[];
}

export interface SpaStep3Response {
  template_id: string;
  template_name: string;
  variables_count: number;
  clauses_count: number;
  message: string;
}
