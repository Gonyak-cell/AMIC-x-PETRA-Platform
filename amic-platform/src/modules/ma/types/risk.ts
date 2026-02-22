export type RiskCategory =
  | "REGULATORY"
  | "FINANCIAL"
  | "LEGAL"
  | "OPERATIONAL"
  | "REPUTATIONAL"
  | "TAX"
  | "ENVIRONMENTAL"
  | "MARKET"
  | "OTHER";

export type RiskSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type RiskLikelihood =
  | "VERY_HIGH"
  | "HIGH"
  | "MEDIUM"
  | "LOW"
  | "VERY_LOW";

export type RiskStatus =
  | "IDENTIFIED"
  | "ASSESSING"
  | "MITIGATING"
  | "MITIGATED"
  | "ACCEPTED"
  | "CLOSED";

export interface RiskItem {
  id: string;
  transaction_id: string;
  category: RiskCategory;
  title: string;
  description: string | null;
  severity: RiskSeverity;
  likelihood: RiskLikelihood;
  risk_score: number | null;
  mitigation_strategy: string | null;
  owner_email: string | null;
  status: RiskStatus;
  due_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskItemCreate {
  category: RiskCategory;
  title: string;
  description?: string;
  severity?: RiskSeverity;
  likelihood?: RiskLikelihood;
  mitigation_strategy?: string;
  owner_email?: string;
  due_date?: string;
  notes?: string;
}

export interface RiskItemUpdate {
  category?: RiskCategory;
  title?: string;
  description?: string;
  severity?: RiskSeverity;
  likelihood?: RiskLikelihood;
  mitigation_strategy?: string;
  owner_email?: string;
  status?: RiskStatus;
  due_date?: string;
  notes?: string;
}

export interface RiskCategorySummary {
  category: RiskCategory;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface RiskMatrixCell {
  severity: RiskSeverity;
  likelihood: RiskLikelihood;
  count: number;
}

export interface RiskSummary {
  total: number;
  by_category: RiskCategorySummary[];
  by_status: Record<string, number>;
  matrix: RiskMatrixCell[];
  avg_risk_score: number;
  unmitigated_critical: number;
}
