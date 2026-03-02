export type EarnoutStatus =
  | "PENDING"
  | "MEASUREMENT_PERIOD"
  | "ACHIEVED"
  | "PARTIALLY_ACHIEVED"
  | "MISSED"
  | "DISPUTED";

export type EarnoutMetric =
  | "REVENUE"
  | "EBITDA"
  | "NET_INCOME"
  | "CUSTOMER_COUNT"
  | "CONTRACT_VALUE"
  | "WORKING_CAPITAL"
  | "OTHER";

export interface EarnoutMilestone {
  id: string;
  transaction_id: string;
  title: string;
  description: string | null;
  metric: EarnoutMetric;
  target_value: string;
  actual_value: string | null;
  currency: string;
  measurement_start: string | null;
  measurement_end: string | null;
  payment_amount: string | null;
  payment_date: string | null;
  status: EarnoutStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface EarnoutCreate {
  title: string;
  description?: string | null;
  metric: EarnoutMetric;
  target_value: number;
  currency?: string;
  measurement_start?: string | null;
  measurement_end?: string | null;
  payment_amount?: number | null;
  notes?: string | null;
}

export interface EarnoutUpdate {
  title?: string;
  description?: string | null;
  metric?: EarnoutMetric;
  target_value?: number;
  actual_value?: number | null;
  currency?: string;
  measurement_start?: string | null;
  measurement_end?: string | null;
  payment_amount?: number | null;
  payment_date?: string | null;
  status?: EarnoutStatus;
  notes?: string | null;
}

export interface EarnoutSummary {
  total: number;
  total_target: string;
  total_actual: string;
  total_payment: string;
  by_status: Record<string, number>;
}
