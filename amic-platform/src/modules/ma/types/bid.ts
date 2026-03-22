export type BidType = "IOI" | "LOI" | "FINAL_OFFER";

export type BidStatus =
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "ACCEPTED"
  | "REJECTED"
  | "WITHDRAWN"
  | "EXPIRED";

export type ValuationMethod =
  | "EV_EBITDA"
  | "EV_REVENUE"
  | "PRICE_BOOK"
  | "DCF"
  | "COMPARABLE"
  | "OTHER";

export interface Bid {
  id: string;
  transaction_id: string;
  buyer_candidate_id: string;
  bid_type: BidType;
  status: BidStatus;
  amount: number | null;
  currency: string;
  valuation_method: ValuationMethod | null;
  multiple: number | null;
  submitted_at: string | null;
  valid_until: string | null;
  conditions: string | null;
  exclusivity_period_days: number | null;
  conditions_precedent: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BidCreate {
  buyer_candidate_id: string;
  bid_type: BidType;
  amount?: number;
  currency?: string;
  valuation_method?: ValuationMethod;
  multiple?: number;
  submitted_at?: string;
  valid_until?: string;
  conditions?: string;
  notes?: string;
}

export interface BidUpdate {
  bid_type?: BidType;
  status?: BidStatus;
  amount?: number;
  currency?: string;
  valuation_method?: ValuationMethod;
  multiple?: number;
  submitted_at?: string;
  valid_until?: string;
  conditions?: string;
  notes?: string;
}

export interface BidComparisonItem {
  buyer_id: string;
  buyer_name: string;
  buyer_type: string;
  ioi: Bid | null;
  loi: Bid | null;
  final_offer: Bid | null;
}

export interface BidImportResult {
  bid: Bid;
  attachment_id: string;
  attachment_file_name: string;
  buyer_name: string;
  created: boolean;
  inferred_fields: string[];
  updated_fields: string[];
  warnings: string[];
}
