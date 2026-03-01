export interface PefFund {
  id: string;
  pef_name: string;
  legal_basis: string | null;
  registration_date: string | null;
  gp1: string | null;
  gp2: string | null;
  gp3: string | null;
  total_committed_capital: number | null;
}

export interface FIRecommendation {
  gp_name: string;
  matching_funds: PefFund[];
  total_committed_sum: number;
  fund_count: number;
}
