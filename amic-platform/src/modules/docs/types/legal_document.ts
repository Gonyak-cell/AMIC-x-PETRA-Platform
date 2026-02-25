// 법률 문서 타입 정의

export type LegalDocType = "SPA" | "SHA" | "BTA" | "SSA" | "MOU";

export type LegalDocStatus = "DRAFT" | "GENERATING" | "READY" | "FAILED";

export interface LegalDocument {
  id: string;
  transaction_id: string;
  doc_type: LegalDocType;
  title: string;
  status: LegalDocStatus;
  parameters: Record<string, unknown> | null;
  template_version: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface LegalDocumentCreate {
  doc_type: LegalDocType;
  title: string;
  parameters: Record<string, unknown>;
}

// ── 타입별 파라미터 인터페이스 ──────────────────────────────────────────────────

export interface SPAParameters {
  seller_name: string;
  seller_representative: string;
  seller_address: string;
  buyer_name: string;
  buyer_representative: string;
  buyer_address: string;
  target_company_name: string;
  target_corp_reg_no: string;
  total_shares: number;
  transfer_shares: number;
  share_price_per: number;
  total_purchase_price: number;
  signing_date: string;
  closing_date: string;
  warranty_period_months: number;
  escrow_amount: number;
  escrow_period_months: number;
  governing_law: string;
}

export interface ShareholderEntry {
  name: string;
  shares: number;
  pct: number;
}

export interface BoardSeatEntry {
  shareholder: string;
  seats: number;
}

export interface SHAParameters {
  company_name: string;
  shareholders: ShareholderEntry[];
  board_seats_total: number;
  board_seats_by_shareholder: BoardSeatEntry[];
  rofr_included: boolean;
  drag_along_included: boolean;
  tag_along_included: boolean;
  lock_up_months: number;
  non_compete_months: number;
  dividend_policy: string;
  signing_date: string;
  governing_law: string;
}

export interface BTAParameters {
  transferor_name: string;
  transferor_representative: string;
  transferee_name: string;
  transferee_representative: string;
  business_description: string;
  transferred_assets: string[];
  excluded_assets: string[];
  transferred_liabilities: string[];
  total_consideration: number;
  signing_date: string;
  closing_date: string;
  employee_transfer: boolean;
  employee_count: number;
  governing_law: string;
}

export interface SSAParameters {
  company_name: string;
  company_representative: string;
  investor_name: string;
  investor_representative: string;
  new_shares_count: number;
  subscription_price_per: number;
  total_investment: number;
  share_class: string;
  pre_money_valuation: number;
  post_money_valuation: number;
  anti_dilution: string;
  liquidation_preference_x: number;
  board_seats: number;
  signing_date: string;
  investment_date: string;
  use_of_proceeds: string;
  governing_law: string;
}

export interface MOUParameters {
  party_a_name: string;
  party_a_representative: string;
  party_b_name: string;
  party_b_representative: string;
  purpose: string;
  exclusivity_period_days: number;
  exclusivity_start_date: string;
  confidentiality_period_months: number;
  binding_provisions: string[];
  non_binding_provisions: string[];
  signing_date: string;
  governing_law: string;
}

// ── 메타데이터 ─────────────────────────────────────────────────────────────────

export interface LegalDocMeta {
  type: LegalDocType;
  label: string;
  labelKo: string;
  description: string;
  highlights: string[];
}

export const LEGAL_DOC_META: Record<LegalDocType, LegalDocMeta> = {
  SPA: {
    type: "SPA",
    label: "Stock Purchase Agreement",
    labelKo: "주식매매계약",
    description: "주식의 양수도에 관한 기본 계약. 매도인·매수인의 권리·의무를 규정합니다.",
    highlights: ["매도/매수인 조항", "진술 및 보장", "가격 조정", "에스크로"],
  },
  SHA: {
    type: "SHA",
    label: "Shareholders Agreement",
    labelKo: "주주간계약",
    description: "주주간 권리와 의무를 규정하는 계약. 거버넌스, 양도 제한 등을 포함합니다.",
    highlights: ["이사회 구성", "우선매수권", "동반매도권", "락업 조항"],
  },
  BTA: {
    type: "BTA",
    label: "Business Transfer Agreement",
    labelKo: "영업양수도계약",
    description: "사업부문 또는 영업 자산 전체를 이전하는 계약입니다.",
    highlights: ["양도 자산 목록", "직원 이전", "부채 승계", "이행 보증"],
  },
  SSA: {
    type: "SSA",
    label: "Share Subscription Agreement",
    labelKo: "신주인수계약",
    description: "신주 발행을 통한 투자 계약. VC/PE 투자 시 주로 활용됩니다.",
    highlights: ["발행가액", "희석방지", "청산우선권", "이사 선임권"],
  },
  MOU: {
    type: "MOU",
    label: "Memorandum of Understanding",
    labelKo: "양해각서",
    description: "거래 초기 단계에서 상호 이해를 확인하는 문서입니다.",
    highlights: ["독점 협상", "비밀유지", "비구속 조항", "유효기간"],
  },
};
