import type { DealItem } from "./deal";
import type { ReputationScore } from "./analysis";

export interface DashboardSummary {
  total_companies: number;
  total_funds: number;
  total_reits: number;
  total_news: number;
  total_deals: number;
  news_last_7days: number;
  recent_deals: DealItem[];
  risk_companies: ReputationScore[];
}
