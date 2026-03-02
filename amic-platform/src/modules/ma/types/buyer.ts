export type BuyerStatus =
  | "IDENTIFIED"
  | "CONTACTED"
  | "NDA_SENT"
  | "NDA_SIGNED"
  | "CIM_SENT"
  | "INTEREST_CONFIRMED"
  | "IOI_RECEIVED"
  | "IOI_ACCEPTED"
  | "DD_GRANTED"
  | "DD_IN_PROGRESS"
  | "LOI_RECEIVED"
  | "LOI_ACCEPTED"
  | "SELECTED"
  | "REJECTED"
  | "BID_SUBMITTED"
  | "BID_NOT_SUBMITTED"
  | "BID_DROPPED";

export type BuyerType =
  | "STRATEGIC"
  | "FINANCIAL_SPONSOR"
  | "FAMILY_OFFICE"
  | "INDIVIDUAL"
  | "OTHER";

export type BuyerTier = "TIER_1" | "TIER_2" | "TIER_3" | "NOT_TARGET";

export type DealRole =
  | "SOLE_BUYER"
  | "CONSORTIUM_LEAD"
  | "CO_INVESTOR"
  | "FINANCING_PROVIDER";

export interface BuyerCandidate {
  id: string;
  transaction_id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  buyer_type: BuyerType;
  status: BuyerStatus;
  tier: BuyerTier | null;
  deal_role: DealRole | null;
  is_short_listed: boolean;
  corp_code: string | null;
  ioi_value: string | null;
  ioi_date: string | null;
  loi_value: string | null;
  loi_date: string | null;
  final_offer_value: string | null;
  rejection_reason: string | null;
  notes: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface BuyerCandidateCreate {
  company_name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  buyer_type: BuyerType;
  tier?: BuyerTier;
  deal_role?: DealRole;
  corp_code?: string;
  notes?: string;
  extra_data?: Record<string, unknown>;
}

export interface BuyerCandidateUpdate {
  company_name?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  buyer_type?: BuyerType;
  status?: BuyerStatus;
  tier?: BuyerTier;
  deal_role?: DealRole;
  is_short_listed?: boolean;
  corp_code?: string;
  ioi_value?: string | null;
  ioi_date?: string;
  loi_value?: string | null;
  loi_date?: string;
  final_offer_value?: string | null;
  rejection_reason?: string;
  notes?: string;
  extra_data?: Record<string, unknown>;
}

export interface BuyerPipelineSummary {
  total: number;
  by_status: Partial<Record<BuyerStatus, number>>;
  by_tier: Record<string, number>;
  avg_ioi_value: string | null;
  avg_loi_value: string | null;
}

export interface ShortListPromoteRequest {
  buyer_ids: string[];
}

export interface BiddingSummary {
  total_bidders: number;
  bid_submitted: number;
  bid_not_submitted: number;
  bid_dropped: number;
}
