/** 백엔드 검색 타입 값 (ES 인덱스명 기반) */
export type SearchIndexType = "companies" | "funds" | "news" | "deals";

/** 백엔드 검색 결과 아이템 (GET /search → items[]) */
export interface SearchResultItem {
  index: string;
  id: string;
  score: number;
  source: Record<string, unknown>;
}

/** 검색 응답 래퍼 */
export interface SearchResponse {
  total: number;
  page: number;
  size: number;
  query: string;
  items: SearchResultItem[];
}

export interface SearchParams {
  q: string;
  type?: SearchIndexType;
  page?: number;
  size?: number;
}
