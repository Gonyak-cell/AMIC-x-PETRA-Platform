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

// --- 검색 유형 ---
export interface SearchTypeOption {
  value: string;
  label: string;
  placeholder: string;
}

export const SEARCH_TYPE_OPTIONS: SearchTypeOption[] = [
  { value: "name", label: "기업명", placeholder: "기업명 또는 종목명 검색..." },
  { value: "stock_code", label: "종목코드", placeholder: "종목코드 입력 (예: 005930)" },
  { value: "jurir_no", label: "법인등록번호", placeholder: "법인등록번호 13자리 입력..." },
  { value: "bizr_no", label: "사업자번호", placeholder: "사업자등록번호 10자리 입력..." },
];
