import type { BadgeVariant } from "@/components/ui";

export interface FilterOption {
  value: string;
  label: string;
}

// --- 시장 구분 (법인구분) ---
export const CORP_CLS_OPTIONS: FilterOption[] = [
  { value: "Y", label: "KOSPI" },
  { value: "K", label: "KOSDAQ" },
  { value: "N", label: "KONEX" },
  { value: "E", label: "기타" },
];

// --- Badge variant 매핑 ---
export const CORP_CLS_BADGE_VARIANT: Record<string, BadgeVariant> = {
  Y: "info",
  K: "success",
  N: "warning",
  E: "neutral",
};

// --- 라벨 매핑 ---
export const CORP_CLS_LABELS: Record<string, string> = {
  Y: "KOSPI",
  K: "KOSDAQ",
  N: "KONEX",
  E: "기타",
};
