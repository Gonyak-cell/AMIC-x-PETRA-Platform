export type ContractType = "SPA" | "AMENDMENT" | "SIDE_LETTER" | "SHAREHOLDERS_AGREEMENT" | "ESCROW_AGREEMENT" | "BTA" | "SSA" | "OTHER";

export type ContractStatus = "DRAFT" | "UNDER_REVIEW" | "PENDING_SIGNATURE" | "PARTIALLY_SIGNED" | "FULLY_EXECUTED" | "TERMINATED";

export type SignatureStatus = "NOT_REQUIRED" | "PENDING" | "SIGNED" | "DECLINED";

export interface Contract {
  id: string;
  transaction_id: string;
  contract_type: ContractType;
  status: ContractStatus;
  title: string;
  description: string | null;
  counterparty_name: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  current_version: number;
  document_url: string | null;
  seller_signature: SignatureStatus;
  buyer_signature: SignatureStatus;
  ai_analysis_summary: string | null;
  ai_risk_flags: AIRiskFlag[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractCreate {
  contract_type?: ContractType;
  title: string;
  description?: string;
  counterparty_name?: string;
  effective_date?: string;
  expiry_date?: string;
  document_url?: string;
  notes?: string;
}

export interface ContractUpdate {
  contract_type?: ContractType;
  status?: ContractStatus;
  title?: string;
  description?: string;
  counterparty_name?: string;
  effective_date?: string;
  expiry_date?: string;
  document_url?: string;
  seller_signature?: SignatureStatus;
  buyer_signature?: SignatureStatus;
  notes?: string;
}

export interface ContractVersion {
  id: string;
  contract_id: string;
  version_number: number;
  changes_summary: string | null;
  document_url: string;
  created_by_email: string | null;
  file_size_bytes: number | null;
  file_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractVersionCreate {
  changes_summary?: string;
  document_url: string;
  created_by_email?: string;
  file_size_bytes?: number;
  file_name?: string;
}

export interface ContractSummary {
  total: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  pending_signatures: number;
  fully_executed: number;
}

export interface AIRiskFlag {
  clause: string;
  risk_level: string;
  description: string;
}

export interface AIAnalysisResult {
  status: string;
  message: string;
  clauses: AIRiskFlag[];
}
