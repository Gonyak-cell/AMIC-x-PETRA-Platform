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
  | "REJECTED";

export type BuyerType = "STRATEGIC" | "FINANCIAL_SPONSOR" | "FAMILY_OFFICE" | "INDIVIDUAL" | "OTHER";

export interface BuyerCandidate {
  id: string;
  transaction_id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  buyer_type: BuyerType;
  status: BuyerStatus;
  ioi_value: number | null;
  ioi_date: string | null;
  loi_value: number | null;
  loi_date: string | null;
  final_offer_value: number | null;
  rejection_reason: string | null;
  notes: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BuyerCandidateCreate {
  company_name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  buyer_type: BuyerType;
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
  ioi_value?: number;
  ioi_date?: string;
  loi_value?: number;
  loi_date?: string;
  final_offer_value?: number;
  rejection_reason?: string;
  notes?: string;
  extra_data?: Record<string, unknown>;
}

export interface BuyerPipelineSummary {
  total: number;
  by_status: Record<BuyerStatus, number>;
  avg_ioi_value: number | null;
  avg_loi_value: number | null;
}
