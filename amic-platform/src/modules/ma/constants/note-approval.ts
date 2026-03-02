import type { SelectOption } from "@/components/ui";

// ── Note Type (Phase 5A) ───────────────────────────────
export const NOTE_TYPE_OPTIONS: SelectOption[] = [
  { value: "COMMENT", label: "코멘트" },
  { value: "DECISION", label: "결정사항" },
  { value: "QUESTION", label: "질문" },
  { value: "ACTION_ITEM", label: "액션아이템" },
];

// ── Approval Type (Phase 5A) ──────────────────────────
export const APPROVAL_TYPE_OPTIONS: SelectOption[] = [
  { value: "PHASE_ADVANCE", label: "단계 전환" },
  { value: "STATUS_CHANGE", label: "상태 변경" },
  { value: "CONTRACT_SIGN", label: "계약 체결" },
  { value: "DEAL_TERMS", label: "거래 조건" },
];

export const APPROVAL_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "대기" },
  { value: "APPROVED", label: "승인" },
  { value: "REJECTED", label: "거절" },
  { value: "CANCELLED", label: "취소" },
];
