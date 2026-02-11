export type SearchResultType = "company" | "fund" | "reit" | "news";

export interface SearchResult {
  type: SearchResultType;
  id: string;
  name: string;
  description: string | null;
  score: number;
}

export interface SearchParams {
  q: string;
  type?: SearchResultType;
  page?: number;
  size?: number;
}
