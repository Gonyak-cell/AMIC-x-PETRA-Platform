import type { SelectOption } from "@/components/ui";

// ── NDA Type ────────────────────────────────────────
export const NDA_TYPE_OPTIONS: SelectOption[] = [
  { value: "ONE_WAY", label: "단방향 (One-Way)" },
  { value: "MUTUAL", label: "상호 (Mutual)" },
];

export const NDA_STATUS_OPTIONS: SelectOption[] = [
  { value: "DRAFT", label: "초안" },
  { value: "SENT", label: "발송" },
  { value: "SIGNED", label: "체결" },
  { value: "EXPIRED", label: "만료" },
  { value: "REJECTED", label: "거절" },
];

// ── Bid Type ────────────────────────────────────────
export const BID_TYPE_OPTIONS: SelectOption[] = [
  { value: "IOI", label: "IOI" },
  { value: "LOI", label: "LOI" },
  { value: "FINAL_OFFER", label: "최종 제안" },
];

export const BID_STATUS_OPTIONS: SelectOption[] = [
  { value: "SUBMITTED", label: "제출" },
  { value: "UNDER_REVIEW", label: "검토 중" },
  { value: "ACCEPTED", label: "수락" },
  { value: "REJECTED", label: "거절" },
  { value: "WITHDRAWN", label: "철회" },
  { value: "EXPIRED", label: "만료" },
];

export const VALUATION_METHOD_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "EV_EBITDA", label: "EV/EBITDA" },
  { value: "EV_REVENUE", label: "EV/Revenue" },
  { value: "PRICE_BOOK", label: "P/B" },
  { value: "DCF", label: "DCF" },
  { value: "COMPARABLE", label: "유사기업 비교" },
  { value: "OTHER", label: "기타" },
];
