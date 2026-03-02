import type { SelectOption } from "@/components/ui";
import type {
  RFIStatus,
  RFICategory,
  RFIItemPriority,
  RFIItemStatus,
} from "../types/rfi";

// ── RFI Status ───────────────────────────────────────
export const RFI_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "DRAFT", label: "초안" },
  { value: "SENT", label: "발송됨" },
  { value: "PARTIALLY_RESPONDED", label: "일부 응답" },
  { value: "FULLY_RESPONDED", label: "전체 응답" },
  { value: "CLOSED", label: "마감" },
  { value: "CANCELLED", label: "취소" },
];

// ── RFI Category ─────────────────────────────────────
export const RFI_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "GENERAL", label: "일반" },
  { value: "FINANCIAL", label: "재무" },
  { value: "TAX", label: "세무" },
  { value: "LEGAL", label: "법률" },
  { value: "OPERATIONAL", label: "운영" },
  { value: "COMMERCIAL", label: "영업" },
  { value: "HR", label: "인사" },
  { value: "IT", label: "IT" },
  { value: "ENVIRONMENTAL", label: "환경" },
  { value: "INSURANCE", label: "보험" },
  { value: "IP", label: "지재권" },
  { value: "REAL_ESTATE", label: "부동산" },
  { value: "VALUATION", label: "밸류에이션" },
  { value: "OTHER", label: "기타" },
];

// ── RFI Priority ─────────────────────────────────────
export const RFI_PRIORITY_OPTIONS: SelectOption[] = [
  { value: "CRITICAL", label: "긴급" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

// ── RFI Item Status ──────────────────────────────────
export const RFI_ITEM_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "PENDING", label: "대기" },
  { value: "RESPONDED", label: "응답됨" },
  { value: "CLARIFICATION_NEEDED", label: "추가확인" },
  { value: "ACCEPTED", label: "확인완료" },
  { value: "NOT_APPLICABLE", label: "해당없음" },
];

// ── RFI Labels (공용 -- 컴포넌트 간 중복 제거) ──────────

export const RFI_STATUS_LABELS: Record<RFIStatus, string> = {
  DRAFT: "초안",
  SENT: "발송됨",
  PARTIALLY_RESPONDED: "일부 응답",
  FULLY_RESPONDED: "전체 응답",
  CLOSED: "마감",
  CANCELLED: "취소",
};

export const RFI_CATEGORY_LABELS: Record<RFICategory, string> = {
  GENERAL: "일반",
  FINANCIAL: "재무",
  TAX: "세무",
  LEGAL: "법률",
  OPERATIONAL: "운영",
  COMMERCIAL: "영업",
  HR: "인사",
  IT: "IT",
  ENVIRONMENTAL: "환경",
  INSURANCE: "보험",
  IP: "지재권",
  REAL_ESTATE: "부동산",
  VALUATION: "밸류에이션",
  OTHER: "기타",
};

export const RFI_PRIORITY_LABELS: Record<RFIItemPriority, string> = {
  CRITICAL: "긴급",
  HIGH: "높음",
  MEDIUM: "보통",
  LOW: "낮음",
};

export const RFI_ITEM_STATUS_LABELS: Record<RFIItemStatus, string> = {
  PENDING: "대기",
  RESPONDED: "응답됨",
  CLARIFICATION_NEEDED: "추가확인",
  ACCEPTED: "확인완료",
  NOT_APPLICABLE: "해당없음",
};
