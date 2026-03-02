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

export interface FIRecommendation {
  gp_name: string;
  /** Decimal → string 직렬화 (BE @field_serializer) */
  min_fund_size: string;
  matching_funds: PefFund[];
  /** Decimal → string 직렬화 (BE @field_serializer) */
  total_committed_sum: string;
  fund_count: number;
  match_reason: string;
}
