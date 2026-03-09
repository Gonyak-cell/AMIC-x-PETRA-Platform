import type { SelectOption } from "@/components/ui";

// ── Deal Type ─────────────────────────────────────────
export const DEAL_TYPE_OPTIONS: SelectOption[] = [
  { value: "SE", label: "SE — 매각 자문" },
  { value: "BU", label: "BU — 인수" },
  { value: "ISSUE", label: "ISSUE — 신주유치" },
  { value: "HYB", label: "HYB — 매각+신주유치" },
  { value: "GEN", label: "GEN — 기타자문" },
];

// ── Transaction Status ────────────────────────────────
export const TRANSACTION_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "DRAFT", label: "초안" },
  { value: "ACTIVE", label: "진행 중" },
  { value: "ON_HOLD", label: "보류" },
  { value: "COMPLETED", label: "완료" },
  { value: "TERMINATED", label: "종료" },
];

// ── Currency ──────────────────────────────────────────
export const CURRENCY_OPTIONS: SelectOption[] = [
  { value: "KRW", label: "KRW (원)" },
  { value: "USD", label: "USD ($)" },
  { value: "EUR", label: "EUR (€)" },
  { value: "JPY", label: "JPY (¥)" },
  { value: "CNY", label: "CNY (¥)" },
];

// ── Deal Structure ────────────────────────────────────
export const DEAL_STRUCTURE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "SHARE_ACQUISITION", label: "지분인수" },
  { value: "ASSET_ACQUISITION", label: "자산인수" },
  { value: "MERGER", label: "합병" },
  { value: "CORPORATE_SPLIT", label: "분할" },
  { value: "MBO", label: "경영진 인수 (MBO)" },
  { value: "OTHER", label: "기타" },
];

// ── Investment Type ───────────────────────────────────
export const INVESTMENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "EQUITY", label: "지분투자" },
  { value: "DEBT", label: "채권투자" },
  { value: "MEZZANINE", label: "메자닌" },
  { value: "CONVERTIBLE", label: "전환사채" },
  { value: "OTHER", label: "기타" },
];

// ── Sale Process (매각 프로세스) ─────────────────────
export const SALE_PROCESS_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "COMPETITIVE_LIMITED", label: "제한적 경쟁입찰" },
  { value: "COMPETITIVE_OPEN", label: "공개 경쟁입찰" },
  { value: "NEGOTIATED", label: "수의계약" },
];

// ── Control Transfer (경영권 이전) ──────────────────
export const CONTROL_TRANSFER_OPTIONS: SelectOption[] = [
  { value: "", label: "미정" },
  { value: "BUYOUT", label: "경영권 포함" },
  { value: "MINORITY", label: "소수지분" },
];

// ── Valuation Basis (밸류에이션 기준) ────────────────
export const VALUATION_BASIS_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "ENTERPRISE_VALUE", label: "EV 기준" },
  { value: "PRE_MONEY_EQUITY", label: "Pre-money Equity 기준" },
];

// ── Cross Border (국경간 거래) ──────────────────────
export const CROSS_BORDER_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "DOMESTIC", label: "국내" },
  { value: "OUTBOUND", label: "아웃바운드" },
  { value: "INBOUND", label: "인바운드" },
];

// ── Target Buyer Type (매수인 유형 - 멀티셀렉트) ────
export const TARGET_BUYER_TYPE_OPTIONS: SelectOption[] = [
  { value: "STRATEGIC", label: "SI (전략적 투자자)" },
  { value: "FINANCIAL_SPONSOR", label: "FI (재무적 투자자)" },
];
