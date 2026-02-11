export type StatusTag = "rising" | "stable" | "risk";

export interface ReputationScore {
  corp_code: string;
  corp_name: string | null;
  total_score: number;
  trend_score: number;
  news_score: number;
  performance_score: number;
  status_tag: StatusTag;
}
