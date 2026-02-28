/** IB 매체 기사 아이템 (Fact / Opinion 공통) */
export interface IBArticleItem {
  id: number;
  title: string;
  lead_text: string | null;
  canonical_url: string;
  source: string;
  published_at: string | null;
  category: string | null;
  category_display: string;
  sentiment_score: number | null;
  is_paywalled: boolean;
}

/** GP별 IB 인사이트 응답 */
export interface IBInsightResponse {
  corp_code: string;
  corp_name: string;
  total_articles: number;
  facts: IBArticleItem[];
  opinions: IBArticleItem[];
  last_collected_at: string | null;
  disclaimer: string;
}

/** IB 기사 목록 응답 */
export interface IBArticleListResponse {
  items: IBArticleItem[];
  total: number;
  page: number;
  size: number;
}

/** IB 수집 결과 응답 */
export interface IBCollectResponse {
  results: Record<
    string,
    { collected: number; new: number; duplicates: number }
  >;
  classified: number;
}
