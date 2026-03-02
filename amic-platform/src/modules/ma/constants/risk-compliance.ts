import type { SelectOption } from "@/components/ui";

// ── Risk Category (Phase 5B) ───────────────────────────
export const RISK_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "REGULATORY", label: "규제 (Regulatory)" },
  { value: "FINANCIAL", label: "재무 (Financial)" },
  { value: "LEGAL", label: "법률 (Legal)" },
  { value: "OPERATIONAL", label: "운영 (Operational)" },
  { value: "REPUTATIONAL", label: "평판 (Reputational)" },
  { value: "TAX", label: "세무 (Tax)" },
  { value: "ENVIRONMENTAL", label: "환경 (Environmental)" },
  { value: "MARKET", label: "시장 (Market)" },
  { value: "OTHER", label: "기타" },
];

export const RISK_SEVERITY_OPTIONS: SelectOption[] = [
  { value: "CRITICAL", label: "치명적" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

export const RISK_LIKELIHOOD_OPTIONS: SelectOption[] = [
  { value: "VERY_HIGH", label: "매우 높음" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
  { value: "VERY_LOW", label: "매우 낮음" },
];

export const RISK_STATUS_OPTIONS: SelectOption[] = [
  { value: "IDENTIFIED", label: "식별" },
  { value: "ASSESSING", label: "평가 중" },
  { value: "MITIGATING", label: "완화 중" },
  { value: "MITIGATED", label: "완화됨" },
  { value: "ACCEPTED", label: "수용" },
  { value: "CLOSED", label: "종료" },
];

// ── Compliance Category (Phase 5B) ─────────────────────
export const COMPLIANCE_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "ANTITRUST", label: "독점규제 (Antitrust)" },
  { value: "FOREIGN_INVESTMENT", label: "외국인투자 (FDI)" },
  { value: "SECURITIES", label: "증권 (Securities)" },
  { value: "DATA_PRIVACY", label: "개인정보 (Data Privacy)" },
  { value: "ANTI_CORRUPTION", label: "반부패 (Anti-Corruption)" },
  { value: "SANCTIONS", label: "제재 (Sanctions)" },
  { value: "ENVIRONMENTAL", label: "환경 (Environmental)" },
  { value: "LABOR", label: "노동 (Labor)" },
  { value: "TAX", label: "세무 (Tax)" },
  { value: "PERMITS", label: "인허가 (Permits)" },
  { value: "OTHER", label: "기타" },
];

export const COMPLIANCE_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_STARTED", label: "미시작" },
  { value: "IN_REVIEW", label: "검토 중" },
  { value: "PENDING_APPROVAL", label: "승인 대기" },
  { value: "APPROVED", label: "승인" },
  { value: "FLAGGED", label: "주의" },
  { value: "NON_COMPLIANT", label: "미준수" },
  { value: "WAIVED", label: "면제" },
];

// ── Permit Filing Type (인허가 신고유형) ──────────────────
export const PERMIT_FILING_TYPE_OPTIONS: SelectOption[] = [
  { value: "CHANGE_NOTIFICATION", label: "변경신고" },
  { value: "CHANGE_APPROVAL", label: "변경허가" },
  { value: "NEW_REGISTRATION", label: "신규등록/허가" },
  { value: "RENEWAL", label: "갱신" },
];

// ── Permit Timing Type (인허가 사전/사후) ─────────────────
export const PERMIT_TIMING_TYPE_OPTIONS: SelectOption[] = [
  { value: "PRE_FILING", label: "사전" },
  { value: "POST_FILING", label: "사후" },
  { value: "BOTH", label: "사전+사후" },
];

// ── Permit Requirement Status (인허가 요건 상태) ──────────
export const PERMIT_REQUIREMENT_STATUS_OPTIONS: SelectOption[] = [
  { value: "IDENTIFIED", label: "확인됨" },
  { value: "DOCUMENTS_PREPARING", label: "서류 준비 중" },
  { value: "FILED", label: "신고 완료" },
  { value: "APPROVED", label: "승인" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];
