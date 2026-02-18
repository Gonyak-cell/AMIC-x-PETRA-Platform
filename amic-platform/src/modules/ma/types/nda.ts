export type NdaType = "ONE_WAY" | "MUTUAL";

export type NdaStatus = "DRAFT" | "SENT" | "SIGNED" | "EXPIRED" | "REJECTED";

export interface NDA {
  id: string;
  transaction_id: string;
  buyer_candidate_id: string;
  nda_type: NdaType;
  status: NdaStatus;
  sent_at: string | null;
  signed_at: string | null;
  expires_at: string | null;
  document_url: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface NDACreate {
  buyer_candidate_id: string;
  nda_type?: NdaType;
  sent_at?: string;
  expires_at?: string;
  document_url?: string;
  notes?: string;
}

export interface NDAUpdate {
  nda_type?: NdaType;
  status?: NdaStatus;
  sent_at?: string;
  signed_at?: string;
  expires_at?: string;
  document_url?: string;
  notes?: string;
}

export interface NDASummary {
  total: number;
  by_status: Record<string, number>;
  signed_count: number;
  pending_count: number;
}
