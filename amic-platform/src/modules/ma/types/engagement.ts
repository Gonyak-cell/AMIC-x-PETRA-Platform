export type EngagementType = "EXCLUSIVE" | "NON_EXCLUSIVE" | "CO_ADVISORY";

export type WorkingGroupRole =
  | "LEAD_ADVISOR"
  | "LEGAL_COUNSEL"
  | "ACCOUNTING_ADVISOR"
  | "TAX_ADVISOR"
  | "INDUSTRY_EXPERT"
  | "VALUATION_ADVISOR"
  | "OTHER";

export interface FeeStructure {
  retainer_fee?: number;
  success_fee_rate?: number;
  minimum_fee?: number;
  expense_cap?: number;
  notes?: string;
}

export interface Engagement {
  id: string;
  transaction_id: string;
  type: EngagementType;
  fee_structure: FeeStructure;
  signed_at: string | null;
  expires_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface EngagementCreate {
  type: EngagementType;
  fee_structure?: FeeStructure;
  signed_at?: string;
  expires_at?: string;
  notes?: string;
}

export interface EngagementUpdate {
  type?: EngagementType;
  fee_structure?: FeeStructure;
  signed_at?: string;
  expires_at?: string;
  notes?: string;
}

export interface WorkingGroupMember {
  id: string;
  transaction_id: string;
  name: string;
  email: string;
  organization: string | null;
  role: WorkingGroupRole;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkingGroupMemberCreate {
  name: string;
  email: string;
  organization?: string;
  role: WorkingGroupRole;
  phone?: string;
}
