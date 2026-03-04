export interface PefFund {
  id: string;
  pef_name: string;
  legal_basis: string | null;
  registration_date: string | null;
  gp1: string | null;
  gp2: string | null;
  gp3: string | null;
  /** Decimal → string 직렬화 (BE @field_serializer) */
  total_committed_capital: string | null;
}

export interface GpProfileOut {
  raw_name: string;
  /** Decimal → string 직렬화 (BE @field_serializer) */
  min_threshold: string | null;
  portfolio_sectors: string[] | null;
  portfolio_companies: string[] | null;
  recent_pef_count: number | null;
  total_pef_count: number | null;
}

export interface FIRecommendation {
  gp_name: string;
  gp_profile: GpProfileOut | null;
  tier: 1 | 2;
  /** Decimal → float 직렬화 (BE @field_serializer) */
  min_fund_size: number;
  matching_funds: PefFund[];
  /** Decimal → float 직렬화 (BE @field_serializer) */
  total_committed_sum: number;
  fund_count: number;
  match_reason: string;
}
