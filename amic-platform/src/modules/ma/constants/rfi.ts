import type { SelectOption } from "@/components/ui";
import type {
  RFIItemStatusV2,
  RFICategoryV2,
  RFIPriority,
} from "../types/rfi";

// ── RFI Item Status (V2) ────────────────────────────────
export const RFI_ITEM_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "OPEN", label: "미답변" },
  { value: "ANSWERED", label: "답변완료" },
  { value: "CLARIFICATION_NEEDED", label: "추가확인" },
  { value: "CLOSED", label: "마감" },
];

// ── RFI Category (V2) ───────────────────────────────────
export const RFI_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "FINANCIAL", label: "재무" },
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
  { value: "CORPORATE", label: "법인" },
  { value: "TAX", label: "세무" },
  { value: "OTHER", label: "기타" },
];

// ── RFI Priority ────────────────────────────────────────
export const RFI_PRIORITY_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

// ── Labels ──────────────────────────────────────────────

export const RFI_ITEM_STATUS_LABELS: Record<RFIItemStatusV2, string> = {
  OPEN: "미답변",
  ANSWERED: "답변완료",
  CLARIFICATION_NEEDED: "추가확인",
  CLOSED: "마감",
};

export const RFI_CATEGORY_LABELS: Record<RFICategoryV2, string> = {
  FINANCIAL: "재무",
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
  CORPORATE: "법인",
  TAX: "세무",
  OTHER: "기타",
};

export const RFI_PRIORITY_LABELS: Record<RFIPriority, string> = {
  HIGH: "높음",
  MEDIUM: "보통",
  LOW: "낮음",
};
