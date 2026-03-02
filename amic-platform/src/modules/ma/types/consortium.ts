export type ConsortiumStatus = "TAPPING" | "CONFIRMED" | "DROPPED";

export interface ConsortiumMapping {
  id: string;
  transaction_id: string;
  lead_buyer_id: string;
  lead_buyer_name: string;
  co_investor_buyer_id: string;
  co_investor_buyer_name: string;
  status: ConsortiumStatus;
  equity_share_pct: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsortiumMappingCreate {
  lead_buyer_id: string;
  co_investor_buyer_id: string;
  status?: ConsortiumStatus;
  equity_share_pct?: number;
  notes?: string;
}

export interface ConsortiumMappingUpdate {
  status?: ConsortiumStatus;
  equity_share_pct?: number;
  notes?: string;
}
