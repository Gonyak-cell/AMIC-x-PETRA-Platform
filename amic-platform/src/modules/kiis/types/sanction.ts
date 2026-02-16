export type SanctionSeverity = "caution" | "warning" | "critical";

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
  items: ClassifiedSanctionListItem[];
}

/** 제재 요약 응답 */
export interface SanctionSummaryResponse {
  total: number;
  caution_count: number;
  warning_count: number;
  critical_count: number;
}

/** 제재 목록 조회 파라미터 */
export interface SanctionListParams {
  severity?: SanctionSeverity;
  page?: number;
  size?: number;
}

/** 분류된 제재 상세 정보 */
export interface ClassifiedSanctionItem {
  id: number;
  company_id: number;
  corp_code: string;
  sanctions_type: string;
  sanctions_detail: string | null;
  sanctions_date: string | null;
  sanctions_agency: string | null;
  severity: string;
  severity_reason: string | null;
  category: string | null;
  classified_at: string | null;
}

/** 제재 분류 실행 응답 (POST /sanctions/classify/{corpCode}) */
export interface SanctionClassifyResponse {
  corp_code: string;
  classified_count: number;
  items: ClassifiedSanctionItem[];
}
