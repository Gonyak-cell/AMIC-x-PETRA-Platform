export interface PhaseSummary {
  phase: string;
  count: number;
  total_value: string | null;
}

export interface DashboardStats {
  total_transactions: number;
  active_transactions: number;
  total_deal_value: string | null;
  by_phase: PhaseSummary[];
  by_status: Record<string, number>;
  by_side: Record<string, number>;
  recent_activity_count: number;
}
