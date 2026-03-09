export type DealType = "SE" | "BU" | "ISSUE" | "HYB" | "GEN";

export type TransactionSide = "SELL" | "BUY" | "DUAL";

export type TransactionPhase =
  | "ENGAGEMENT"
  | "PREPARATION"
  | "MARKETING"
  | "BIDDING"
  | "MOU_SIGNED" // deprecated: 마일스톤으로 전환, PG enum 제거 불가하여 유지
  | "MAIN_DUE_DILIGENCE"
  | "NEGOTIATION"
  | "CLOSING"
  | "POST_CLOSING";

export type TransactionStatus =
  | "DRAFT"
  | "ACTIVE"
  | "ON_HOLD"
  | "COMPLETED"
  | "TERMINATED";

export type DealStructure =
  | "SHARE_ACQUISITION"
  | "ASSET_ACQUISITION"
  | "MERGER"
  | "CORPORATE_SPLIT"
  | "MBO"
  | "OTHER";

export type InvestmentType =
  | "EQUITY"
  | "DEBT"
  | "MEZZANINE"
  | "CONVERTIBLE"
  | "OTHER";

export type Currency = "KRW" | "USD" | "EUR" | "JPY" | "CNY";

export type SaleProcess =
  | "COMPETITIVE_LIMITED"
  | "COMPETITIVE_OPEN"
  | "NEGOTIATED";
export type ControlTransfer = "BUYOUT" | "MINORITY";
export type ValuationBasis = "ENTERPRISE_VALUE" | "PRE_MONEY_EQUITY";
export type CrossBorder = "DOMESTIC" | "OUTBOUND" | "INBOUND";
export type TargetBuyerType = "STRATEGIC" | "FINANCIAL_SPONSOR";

export interface Transaction {
  id: string;
  code_name: string;
  name: string;
  deal_type: DealType;
  side: TransactionSide;
  phase: TransactionPhase;
  status: TransactionStatus;
  target_company_name: string;
  target_corp_code: string | null;
  client_name: string;
  estimated_deal_value: string | null;
  currency: Currency;
  deal_structure: DealStructure | null;
  investment_type: InvestmentType | null;
  industry: string | null;
  lead_advisor_email: string;
  deal_captain_email: string | null;
  target_close_date: string | null;
  // Deal Terms
  sale_process: SaleProcess | null;
  control_transfer: ControlTransfer | null;
  target_stake: string | null;
  new_share_ratio: string | null;
  old_share_ratio: string | null;
  valuation_basis: ValuationBasis | null;
  cross_border: CrossBorder | null;
  target_buyer_types: TargetBuyerType[] | null;
  exclusivity: boolean | null;
  exclusivity_deadline: string | null;

  fdd_deal_id: string | null;
  im_document_id: string | null;
  notes: string | null;
  corporate_info: Record<string, unknown> | null;
  financial_summary: Record<string, unknown> | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreate {
  name: string;
  deal_type: DealType;
  side: TransactionSide;
  target_company_name: string;
  target_corp_code?: string;
  client_name: string;
  estimated_deal_value?: string;
  currency?: Currency;
  deal_structure?: DealStructure;
  investment_type?: InvestmentType;
  industry?: string;
  lead_advisor_email: string;
  deal_captain_email?: string;
  target_close_date?: string;
  // Deal Terms
  sale_process?: SaleProcess;
  control_transfer?: ControlTransfer;
  target_stake?: number;
  new_share_ratio?: number;
  old_share_ratio?: number;
  valuation_basis?: ValuationBasis;
  cross_border?: CrossBorder;
  target_buyer_types?: TargetBuyerType[];
  exclusivity?: boolean;
  exclusivity_deadline?: string;
  notes?: string;
}

export interface TransactionUpdate {
  name?: string;
  deal_type?: DealType;
  side?: TransactionSide;
  target_company_name?: string;
  target_corp_code?: string;
  client_name?: string;
  estimated_deal_value?: string | null;
  currency?: Currency;
  deal_structure?: DealStructure | null;
  investment_type?: InvestmentType | null;
  industry?: string | null;
  lead_advisor_email?: string;
  deal_captain_email?: string | null;
  target_close_date?: string | null;
  // Deal Terms
  sale_process?: SaleProcess | null;
  control_transfer?: ControlTransfer | null;
  target_stake?: number | null;
  new_share_ratio?: number | null;
  old_share_ratio?: number | null;
  valuation_basis?: ValuationBasis | null;
  cross_border?: CrossBorder | null;
  target_buyer_types?: TargetBuyerType[] | null;
  exclusivity?: boolean | null;
  exclusivity_deadline?: string | null;
  notes?: string;
}

export interface TransactionListParams {
  search?: string;
  side?: TransactionSide;
  phase?: TransactionPhase;
  status?: TransactionStatus;
  limit?: number;
  offset?: number;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  limit: number;
  offset: number;
}
