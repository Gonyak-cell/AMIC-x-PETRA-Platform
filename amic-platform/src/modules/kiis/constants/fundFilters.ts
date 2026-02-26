import type { BadgeVariant } from "@/components/ui";

export interface FilterOption {
  value: string;
  label: string;
}

// --- 투자 방식 ---
export const FUND_TYPE_OPTIONS: FilterOption[] = [
  { value: "blind", label: "Blind" },
  { value: "project", label: "Project" },
];

// --- 법률상 유형 ---
export const LEGAL_TYPE_OPTIONS: FilterOption[] = [
  { value: "professional_private", label: "기관전용 사모" },
  { value: "general_private", label: "일반 사모 (PEF)" },
  { value: "public", label: "공모" },
];

// --- 자산 유형 ---
export const ASSET_CLASS_OPTIONS: FilterOption[] = [
  { value: "vc", label: "Venture Capital" },
  { value: "pef", label: "Private Equity" },
  { value: "real_estate", label: "부동산" },
  { value: "infra", label: "인프라" },
  { value: "mezzanine", label: "메자닌" },
  { value: "fund_of_funds", label: "재간접 (FoF)" },
];

// --- 펀드 상태 ---
export const FUND_STATUS_OPTIONS: FilterOption[] = [
  { value: "active", label: "운용중" },
  { value: "harvest", label: "회수기간" },
  { value: "liquidated", label: "청산" },
];

// --- 데이터 소스 ---
export const DATA_SOURCE_OPTIONS: FilterOption[] = [
  { value: "", label: "전체" },
  { value: "kofia", label: "KOFIA" },
  { value: "pef_registry", label: "PEF 등록부" },
];

export const DATA_SOURCE_LABELS: Record<string, string> = {
  kofia: "KOFIA",
  pef_registry: "PEF 등록부",
};

// --- 설정액 프리셋 ---
export const AMOUNT_PRESET_OPTIONS: FilterOption[] = [
  { value: "", label: "전체" },
  { value: "0-100", label: "100억 이하" },
  { value: "100-500", label: "100~500억" },
  { value: "500-1000", label: "500~1,000억" },
  { value: "1000-5000", label: "1,000~5,000억" },
  { value: "5000-", label: "5,000억 이상" },
];

// --- Badge variant 매핑 ---
export const ASSET_CLASS_BADGE_VARIANT: Record<string, BadgeVariant> = {
  vc: "info",
  pef: "success",
  real_estate: "warning",
  infra: "neutral",
  mezzanine: "error",
  fund_of_funds: "neutral",
};

export const FUND_STATUS_BADGE_VARIANT: Record<string, BadgeVariant> = {
  active: "success",
  harvest: "warning",
  liquidated: "neutral",
};

// --- 라벨 매핑 ---
export const ASSET_CLASS_LABELS: Record<string, string> = {
  vc: "VC",
  pef: "PEF",
  real_estate: "부동산",
  infra: "인프라",
  mezzanine: "메자닌",
  fund_of_funds: "FoF",
};

export const FUND_STATUS_LABELS: Record<string, string> = {
  active: "운용중",
  harvest: "회수기간",
  liquidated: "청산",
};

// --- 빈티지 연도 옵션 생성 ---
export function getVintageYearOptions(): FilterOption[] {
  const currentYear = new Date().getFullYear();
  const options: FilterOption[] = [{ value: "", label: "전체" }];
  for (let y = currentYear; y >= 2000; y--) {
    options.push({ value: String(y), label: String(y) });
  }
  return options;
}

/** 설정액 프리셋 → { min, max } 변환 */
export function parseAmountPreset(preset: string): { min?: number; max?: number } {
  if (!preset) return {};
  const [minStr, maxStr] = preset.split("-");
  return {
    min: minStr ? Number(minStr) : undefined,
    max: maxStr ? Number(maxStr) : undefined,
  };
}
