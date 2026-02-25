// LDD(법률실사) 보고서 타입 정의

export type LDDReportStatus =
  | "DRAFT"
  | "ANALYZING"
  | "REVIEW"
  | "FINALIZING"
  | "GENERATING"
  | "READY"
  | "FAILED";

export type LDDReportType = "FULL" | "REDFLAG";

export type LDDItemStatus = "OK" | "ISSUE" | "NA" | "PENDING";

export type LDDIssueLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type LDDSectionType =
  | "GOVERNANCE"
  | "CAPITAL"
  | "CONTRACTS"
  | "LITIGATION"
  | "LABOR"
  | "IP"
  | "REAL_ESTATE"
  | "PERMITS"
  | "TAX"
  | "DATA_IT";

// ── 항목(Item) ───────────────────────────────────────────────────────────────

export interface LDDItem {
  item_id: string;
  name: string;
  status: LDDItemStatus;
  issue_level: LDDIssueLevel | null;
  risk_color: string;           // RED | AMBER | GREEN (자동 계산)
  description: string;
  deal_impact: string;          // 거래에 미치는 영향
  recommendation: string;
  rfi_required: boolean;
  rfi_number: string;           // 예: CORP-001
  // AI 분석 메타데이터
  confidence: number;
  evidence_refs: string[];
  // 사용자 리뷰 필드
  user_comment: string;
  user_approved: boolean | null;
  user_override_status: string | null;
  user_override_level: string | null;
}

// ── 섹션(Section) ────────────────────────────────────────────────────────────

export interface LDDSection {
  section_type: LDDSectionType;
  title: string;
  items: LDDItem[];
}

// ── 보고서(Report) ───────────────────────────────────────────────────────────

export interface LDDReport {
  id: string;
  transaction_id: string;
  report_type: LDDReportType;
  title: string;
  status: LDDReportStatus;
  target_company: string | null;
  dd_period: string | null;
  law_firm: string | null;
  prepared_by: string | null;
  sections: LDDSection[] | null;
  total_items: number;
  issue_count: number;
  red_count: number;
  amber_count: number;
  green_count: number;
  ok_count: number;
  na_count: number;
  pending_count: number;
  rfi_count: number;
  template_version: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_by_email: string | null;
  // VDR 연동 + Ralph Loop 워크플로우
  vdr_source: boolean;
  draft_score: number | null;
  final_score: number | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  review_started_at: string | null;
  review_completed_at: string | null;
  finalize_started_at: string | null;
  finalize_completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ── 생성/수정 요청 ───────────────────────────────────────────────────────────

export interface LDDReportCreate {
  title: string;
  report_type: LDDReportType;
  target_company?: string;
  dd_period?: string;
  law_firm?: string;
  prepared_by?: string;
  sections?: LDDSection[];
}

export interface LDDSectionsUpdate {
  sections: LDDSection[];
}

// ── 표시 레이블 / 배지 상수 ──────────────────────────────────────────────────

export const LDD_STATUS_LABELS: Record<LDDReportStatus, string> = {
  DRAFT:      "초안",
  ANALYZING:  "AI 분석 중",
  REVIEW:     "리뷰 대기",
  FINALIZING: "최종 확정 중",
  GENERATING: "생성 중",
  READY:      "완료",
  FAILED:     "실패",
};

export const LDD_STATUS_COLORS: Record<LDDReportStatus, string> = {
  DRAFT:      "bg-slate-100 text-slate-600",
  ANALYZING:  "bg-indigo-100 text-indigo-700",
  REVIEW:     "bg-amber-100 text-amber-700",
  FINALIZING: "bg-purple-100 text-purple-700",
  GENERATING: "bg-blue-100 text-blue-700",
  READY:      "bg-green-100 text-green-700",
  FAILED:     "bg-red-100 text-red-700",
};

export const LDD_REPORT_TYPE_LABELS: Record<LDDReportType, string> = {
  FULL:    "정식 LDD",
  REDFLAG: "Redflag DD",
};

export const LDD_ITEM_STATUS_LABELS: Record<LDDItemStatus, string> = {
  OK:      "이상없음",
  ISSUE:   "이슈",
  NA:      "해당없음",
  PENDING: "미검토",
};

export const LDD_ITEM_STATUS_COLORS: Record<LDDItemStatus, string> = {
  OK:      "bg-green-100 text-green-700",
  ISSUE:   "bg-red-100 text-red-700",
  NA:      "bg-slate-100 text-slate-500",
  PENDING: "bg-yellow-100 text-yellow-700",
};

export const LDD_ISSUE_LEVEL_LABELS: Record<LDDIssueLevel, string> = {
  CRITICAL: "Critical",
  HIGH:     "High",
  MEDIUM:   "Medium",
  LOW:      "Low",
};

export const LDD_ISSUE_LEVEL_COLORS: Record<LDDIssueLevel, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH:     "bg-orange-400 text-white",
  MEDIUM:   "bg-amber-400 text-white",
  LOW:      "bg-green-400 text-white",
};

export const LDD_RISK_COLOR_BADGE: Record<string, string> = {
  RED:   "bg-red-100 text-red-700 border border-red-300",
  AMBER: "bg-amber-100 text-amber-700 border border-amber-300",
  GREEN: "bg-green-100 text-green-700 border border-green-300",
};

export const LDD_SECTION_LABELS: Record<LDDSectionType, string> = {
  GOVERNANCE:  "기업 일반 및 지배구조",
  CAPITAL:     "자본구조 및 주주협약",
  CONTRACTS:   "주요 계약",
  LITIGATION:  "소송 및 분쟁",
  LABOR:       "인사 및 노무",
  IP:          "지식재산권",
  REAL_ESTATE: "부동산 및 환경",
  PERMITS:     "인허가 및 규제",
  TAX:         "조세",
  DATA_IT:     "개인정보 및 IT",
};
