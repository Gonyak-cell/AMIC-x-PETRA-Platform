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

/* ─── 정성적 평판 (GET /analysis/reputation/{corpCode}/qualitative) ─── */

/** 정성적 평판 - 기사 아이템 */
export interface ReputationArticle {
  title: string;
  url: string;
  source: string;
  published_at: string | null;
  sentiment_label: string | null;
}

/** 정성적 평판 - 테마별 그룹 */
export interface ReputationTheme {
  theme_code: string;
  theme_name: string;
  sentiment: "positive" | "negative";
  article_count: number;
  description: string;
  articles: ReputationArticle[];
}

/** 정성적 평판 응답 */
export interface QualitativeReputationResponse {
  corp_code: string;
  months: number;
  total_articles: number;
  positive_count: number;
  negative_count: number;
  themes: ReputationTheme[];
  risk_absences: string[];
}
