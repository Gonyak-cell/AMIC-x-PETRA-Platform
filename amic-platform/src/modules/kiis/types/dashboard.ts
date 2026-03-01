import type { StatusTag } from "./analysis";

/** 데이터 카운트 (label/count 쌍) */
export interface DataCount {
  label: string;
  count: number;
}

/** 최근 딜 (대시보드용 축약) */
export interface RecentDeal {
  target_company: string;
  amount_display: string | null;
  sector: string | null;
  deal_date: string | null;
}

/** 위험 기업 */
export interface RiskCompany {
  corp_code: string | null;
  corp_name: string;
  status_tag: StatusTag;
  total_score: number;
}

/** 데이터 신선도 */
export interface DataFreshness {
  entity: string;
  latest_at: string | null;
  count: number;
}

/** 대시보드 요약 응답 (GET /dashboard/summary) */
export interface DashboardSummary {
  counts: DataCount[];
  recent_news_count: number;
  recent_deals: RecentDeal[];
  risk_companies: RiskCompany[];
  data_freshness: DataFreshness[];
}
