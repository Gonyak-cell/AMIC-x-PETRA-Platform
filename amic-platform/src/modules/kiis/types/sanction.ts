export type SanctionSeverity = "caution" | "warning" | "critical";

/** 제재 상세 아이템 (GET /sanctions/classified/{corpCode} → items[]) */
export interface ClassifiedSanctionItem {
  id: number;
  company_id: number;
  corp_code: string;
  sanctions_type: string;
  sanctions_detail: string | null;
  sanctions_date: string | null;
  sanctions_agency: string | null;
  severity: SanctionSeverity;
  severity_reason: string | null;
  category: string | null;
  classified_at: string | null;
}

/** 제재 목록 아이템 (축약) */
export interface ClassifiedSanctionListItem {
  id: number;
  corp_code: string;
  sanctions_type: string;
  severity: string;
  category: string | null;
  sanctions_date: string | null;
}

/** 제재 목록 래퍼 응답 */
export interface ClassifiedSanctionListResponse {
  total: number;
  page: number;
  size: number;
  items: ClassifiedSanctionItem[];
}

/** 제재 요약 응답 */
export interface SanctionSummaryResponse {
  total: number;
  caution_count: number;
  warning_count: number;
  critical_count: number;
}
