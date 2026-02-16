export type StatusTag = "rising" | "stable" | "risk";

/** 평판 점수 상세 (GET /analysis/reputation/{corpCode}) */
export interface ReputationScore {
  company_id: number;
  corp_code: string;
  corp_name: string;
  trend_score: number;
  news_score: number;
  performance_score: number;
  total_score: number;
  status_tag: StatusTag;
  scored_at: string;
  news_count: number;
  exit_count: number;
}

/** 평판 목록 아이템 (GET /analysis/reputation → items[]) - 축약 */
export interface ReputationListItem {
  company_id: number;
  corp_code: string;
  corp_name: string;
  total_score: number;
  status_tag: StatusTag;
  scored_at: string | null;
}

/** 평판 이력 아이템 */
export interface ReputationHistoryItem {
  total_score: number;
  status_tag: StatusTag;
  trend_score: number;
  news_score: number;
  performance_score: number;
  recorded_at: string;
}

/** 평판 이력 래퍼 응답 (GET /analysis/reputation/{corpCode}/history) */
export interface ReputationHistoryResponse {
  corp_code: string;
  corp_name: string;
  total: number;
  items: ReputationHistoryItem[];
}

/** 평판 목록 래퍼 응답 */
export interface ReputationListResponse {
  total: number;
  page: number;
  size: number;
  items: ReputationListItem[];
}
