import type { SelectOption } from "@/components/ui";

export const DEAL_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "COMPLETION_ACCOUNTS", label: "가격조정 (Completion Accounts)" },
  { value: "LOCKED_BOX", label: "잠금박스 (Locked Box)" },
];

export const CURRENCY_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "KRW", label: "KRW (원)" },
  { value: "USD", label: "USD ($)" },
  { value: "EUR", label: "EUR (€)" },
  { value: "JPY", label: "JPY (¥)" },
];

export const DEAL_STRUCTURE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "SHARE_ACQUISITION", label: "지분인수" },
  { value: "ASSET_ACQUISITION", label: "자산인수" },
  { value: "MERGER", label: "합병" },
  { value: "CORPORATE_SPLIT", label: "분할" },
  { value: "MBO", label: "경영진 인수 (MBO)" },
  { value: "OTHER", label: "기타" },
];

export const INVESTMENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "EQUITY", label: "지분투자" },
  { value: "DEBT", label: "채권투자" },
  { value: "MEZZANINE", label: "메자닌" },
  { value: "CONVERTIBLE", label: "전환사채" },
  { value: "OTHER", label: "기타" },
];

export const SELLER_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "INDIVIDUAL", label: "개인" },
  { value: "CORPORATE", label: "법인" },
  { value: "INSTITUTIONAL", label: "기관투자자" },
  { value: "PE_FUND", label: "PE펀드" },
  { value: "MANAGEMENT", label: "경영진" },
  { value: "OTHER", label: "기타" },
];
