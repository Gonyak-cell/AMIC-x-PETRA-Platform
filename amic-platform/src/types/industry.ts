/**
 * 공유 산업 분류 타입 — FDD/IM 모듈 공통.
 *
 * FDD는 6개 산업 (general ~ logistics)을 지원.
 * IM은 추가로 real_estate, energy, consumer를 지원.
 * 공유 타입은 전체 합집합을 포함한다.
 */

export type IndustryId =
  | "general"
  | "tech"
  | "healthcare"
  | "manufacturing"
  | "financial_services"
  | "logistics"
  | "real_estate"
  | "energy"
  | "consumer";

export interface IndustryInfo {
  id: IndustryId;
  name_kr: string;
  name_en: string;
}

/** 전체 산업 목록 (FDD + IM 합집합). */
export const INDUSTRY_LIST: IndustryInfo[] = [
  { id: "general", name_kr: "일반", name_en: "General" },
  { id: "tech", name_kr: "테크/SaaS", name_en: "Tech / SaaS" },
  { id: "healthcare", name_kr: "헬스케어", name_en: "Healthcare" },
  { id: "manufacturing", name_kr: "제조업", name_en: "Manufacturing" },
  { id: "financial_services", name_kr: "금융서비스", name_en: "Financial Services" },
  { id: "logistics", name_kr: "물류", name_en: "Logistics" },
  { id: "real_estate", name_kr: "부동산", name_en: "Real Estate" },
  { id: "energy", name_kr: "에너지", name_en: "Energy" },
  { id: "consumer", name_kr: "소비재", name_en: "Consumer" },
];

/** Select 옵션용 변환 (전체). */
export const INDUSTRY_OPTIONS = INDUSTRY_LIST.map((i) => ({
  value: i.id,
  label: `${i.name_en} (${i.name_kr})`,
}));

/** FDD 지원 산업 ID 목록. */
export const FDD_INDUSTRY_IDS: IndustryId[] = [
  "general", "tech", "healthcare", "manufacturing", "financial_services", "logistics",
];

export function isIndustryId(value: string): value is IndustryId {
  return INDUSTRY_OPTIONS.some((opt) => opt.value === value);
}

/** FDD 전용 Select 옵션. */
export const FDD_INDUSTRY_OPTIONS = INDUSTRY_LIST
  .filter((i) => FDD_INDUSTRY_IDS.includes(i.id))
  .map((i) => ({ value: i.id, label: `${i.name_en} (${i.name_kr})` }));
