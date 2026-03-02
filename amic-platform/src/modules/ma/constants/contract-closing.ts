import type { SelectOption } from "@/components/ui";

// ── Contract Type (Phase 3) ──────────────────────────
export const CONTRACT_TYPE_OPTIONS: SelectOption[] = [
  { value: "SPA", label: "SPA (주식매매계약)" },
  { value: "SHAREHOLDERS_AGREEMENT", label: "SHA (주주간계약)" },
  { value: "BTA", label: "BTA (영업양수도계약)" },
  { value: "SSA", label: "SSA (신주인수계약)" },
  { value: "AMENDMENT", label: "수정계약" },
  { value: "SIDE_LETTER", label: "사이드레터" },
  { value: "ESCROW_AGREEMENT", label: "에스크로 계약" },
  { value: "OTHER", label: "기타" },
];

export const ISSUE_DECISION_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "미결정" },
  { value: "CONSIDER_ACCEPTING", label: "수용 검토" },
  { value: "CANNOT_ACCEPT", label: "수용 불가" },
];

export const MARKUP_TYPE_OPTIONS: SelectOption[] = [
  { value: "draft", label: "Draft" },
  { value: "1st", label: "1st Markup" },
  { value: "2nd", label: "2nd Markup" },
  { value: "3rd", label: "3rd Markup" },
  { value: "4th", label: "4th Markup" },
  { value: "final", label: "Final" },
];

export const CONTRACT_STATUS_OPTIONS: SelectOption[] = [
  { value: "DRAFT", label: "초안" },
  { value: "UNDER_REVIEW", label: "검토 중" },
  { value: "PENDING_SIGNATURE", label: "서명 대기" },
  { value: "PARTIALLY_SIGNED", label: "일부 서명" },
  { value: "FULLY_EXECUTED", label: "체결 완료" },
  { value: "TERMINATED", label: "종료" },
];

export const SIGNATURE_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_REQUIRED", label: "불필요" },
  { value: "PENDING", label: "대기" },
  { value: "SIGNED", label: "서명 완료" },
  { value: "DECLINED", label: "거절" },
];

// ── Closing Category (Phase 3) ──────────────────────
export const CLOSING_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "REGULATORY", label: "인허가 (Regulatory)" },
  { value: "LEGAL", label: "법률 (Legal)" },
  { value: "FINANCIAL", label: "재무 (Financial)" },
  { value: "CORPORATE", label: "기업 (Corporate)" },
  { value: "CONDITION_PRECEDENT", label: "선행조건 (CP)" },
  { value: "FUND_FLOW", label: "자금이체 (Fund Flow)" },
  { value: "OTHER", label: "기타" },
];

export const CLOSING_CONDITION_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "대기" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "WAIVED", label: "면제" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];
