export type NewsSource = "platum" | "dealsite";

/** 뉴스 목록 아이템 (GET /news → items[]) */
export interface NewsListItem {
  id: number;
  title: string;
  source: string;
  author: string | null;
  published_at: string | null;
  url: string;
  sentiment_score: number | null;
}

/** 뉴스 상세 (GET /news/{articleId}) */
export interface NewsDetail extends NewsListItem {
  content: string | null;
  summary: string | null;
  keywords: string | null;
  company_id: number | null;
}

/** 뉴스 목록 래퍼 응답 */
export interface NewsListResponse {
  total: number;
  page: number;
  size: number;
  items: NewsListItem[];
}

/** 뉴스 수집 응답 */
export interface NewsCollectResponse {
  source: string;
  collected: number;
  duplicates: number;
  new_articles: number;
}

export interface NewsListParams {
  source?: NewsSource;
  date_from?: string;
  date_to?: string;
  company_id?: number;
  page?: number;
  size?: number;
}
