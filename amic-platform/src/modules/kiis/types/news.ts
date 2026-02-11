export type SentimentType = "positive" | "neutral" | "negative";
export type NewsSource = "platum" | "dealsite";

export interface NewsArticle {
  id: string;
  title: string;
  content: string | null;
  source: NewsSource;
  published_at: string;
  url: string | null;
  company_associations: string[];
  sentiment: SentimentType | null;
  sentiment_score: number | null;
}

export interface NewsListParams {
  source?: NewsSource;
  start_date?: string;
  end_date?: string;
  company_id?: string;
  search?: string;
  page?: number;
  size?: number;
}
