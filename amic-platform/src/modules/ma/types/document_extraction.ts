// ── 문서 AI 추출 타입 정의 ─────────────────────────────────

export type DocExtractionCategory =
  | "NDA"
  | "LOI_MOU"
  | "SPA_BTA"
  | "CORPORATE_DOCS"
  | "REGISTRY_DOCS"
  | "BIZ_REG_DOCS"
  | "TAX_FILING"
  | "TEASER_IM"
  | "DD_REPORT"
  | "RFI_RESPONSE"
  | "REFERENCE_ONLY";

export type ExtractionStatus =
  | "PENDING"
  | "CLASSIFYING"
  | "EXTRACTING"
  | "COMPLETED"
  | "FAILED"
  | "CONFIRMED";

export const CATEGORY_LABELS: Record<DocExtractionCategory, string> = {
  NDA: "NDA (비밀유지계약)",
  LOI_MOU: "LOI/MOU (인수의향서)",
  SPA_BTA: "SPA/BTA (주식매매계약)",
  CORPORATE_DOCS: "등기부등본/사업자등록증",
  REGISTRY_DOCS: "법인등기부등본",
  BIZ_REG_DOCS: "사업자등록증",
  TAX_FILING: "세무신고서",
  TEASER_IM: "Teaser/IM",
  DD_REPORT: "DD 보고서",
  RFI_RESPONSE: "RFI 답변서",
  REFERENCE_ONLY: "기타 참고자료",
};

export const STATUS_LABELS: Record<ExtractionStatus, string> = {
  PENDING: "대기중",
  CLASSIFYING: "분류중",
  EXTRACTING: "추출중",
  COMPLETED: "완료 (검토 대기)",
  FAILED: "실패",
  CONFIRMED: "확정",
};

/** 추출 가능 카테고리 (LLM 추출 수행 대상) */
export const EXTRACTABLE_CATEGORIES: Set<DocExtractionCategory> = new Set([
  "NDA",
  "LOI_MOU",
  "SPA_BTA",
  "CORPORATE_DOCS",
  "REGISTRY_DOCS",
  "BIZ_REG_DOCS",
  "TAX_FILING",
]);

/** 진행중 상태 — 폴링이 필요한 상태 */
export const IN_PROGRESS_STATUSES: ExtractionStatus[] = [
  "PENDING",
  "CLASSIFYING",
  "EXTRACTING",
];

/** 완료 상태 — 성공적으로 종료된 상태 */
export const SUCCESS_STATUSES: ExtractionStatus[] = ["COMPLETED", "CONFIRMED"];

/** 매핑 가능 대상 모델 */
export type TargetModel = "nda" | "bid" | "contract" | "transaction";

export const TARGET_MODEL_LABELS: Record<TargetModel, string> = {
  nda: "NDA",
  bid: "입찰 (Bid)",
  contract: "계약 (Contract)",
  transaction: "거래 (Transaction)",
};

// ── API 응답 모델 ──────────────────────────────────────────

export interface DocumentExtraction {
  id: string;
  transaction_id: string;
  vdr_document_id: string;
  doc_category: DocExtractionCategory | null;
  classification_confidence: number | null;
  status: ExtractionStatus;
  error_message: string | null;
  extracted_data: Record<string, unknown> | null;
  target_model: TargetModel | null;
  target_id: string | null;
  llm_cost_usd: number;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractionListResponse {
  items: DocumentExtraction[];
  total: number;
}

// ── 요청 모델 ──────────────────────────────────────────────

export interface ExtractionCreateRequest {
  vdr_document_id: string;
  doc_category_hint?: DocExtractionCategory;
}

export interface BatchExtractionRequest {
  vdr_document_ids: string[];
}

export interface ExtractionConfirmRequest {
  confirmed_data: Record<string, unknown>;
  target_model: TargetModel;
  target_id?: string;
  create_new?: boolean;
}

// ── 카테고리별 추출 데이터 인터페이스 ──────────────────────

export interface NdaExtractedData {
  counterparty_name: string | null;
  nda_type: "ONE_WAY" | "MUTUAL" | null;
  signed_at: string | null;
  expires_at: string | null;
  confidentiality_period_months: number | null;
  jurisdiction: string | null;
}

export interface LoiMouExtractedData {
  proposed_amount: number | null;
  currency: string | null;
  valuation_method: string | null;
  exclusivity_period_days: number | null;
  conditions_precedent: string[] | null;
  valid_until: string | null;
  bid_type: string | null;
}

export interface SpaBtaExtractedData {
  final_purchase_price: number | null;
  currency: string | null;
  closing_date: string | null;
  counterparty_name: string | null;
  effective_date: string | null;
  rw_cap_amount: number | null;
  rw_cap_percentage: number | null;
  indemnification_period_months: number | null;
  contract_type: string | null;
  key_conditions: string[] | null;
  risk_summary: string | null;
}

export interface CorporateDirector {
  position: string;
  name: string;
  birth_date: string | null;
  appointment_date: string | null;
}

const DIRECTOR_POSITION_ORDER = [
  "사내이사/대표이사",
  "대표이사",
  "사내이사",
  "사외이사",
  "감사",
];

/** 임원 목록을 직위 순서대로 정렬 (대표이사 → 사내이사 → 사외이사 → 감사) */
export function sortDirectorsByPosition(
  directors: CorporateDirector[],
): CorporateDirector[] {
  return [...directors].sort((a, b) => {
    const ai = DIRECTOR_POSITION_ORDER.findIndex((p) =>
      a.position?.includes(p),
    );
    const bi = DIRECTOR_POSITION_ORDER.findIndex((p) =>
      b.position?.includes(p),
    );
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
}

export interface CorporateDocsExtractedData {
  company_name: string | null;
  representative_name: string | null;
  establishment_date: string | null;
  business_registration_number: string | null;
  corporate_registration_number: string | null;
  capital_amount: number | null;
  total_shares_issued: number | null;
  par_value_per_share: number | null;
  common_shares: number | null;
  preferred_shares: number | null;
  business_type: string | null;
  business_item: string | null;
  head_office_address: string | null;
  directors: CorporateDirector[] | null;
  corporate_purpose: string | null;
}

export interface TaxFilingExtractedData {
  fiscal_year: string | null;
  revenue: number | null;
  cost_of_goods_sold: number | null;
  gross_profit: number | null;
  sga_expenses: number | null;
  operating_income: number | null;
  non_operating_income: number | null;
  non_operating_expenses: number | null;
  income_before_tax: number | null;
  corporate_tax: number | null;
  net_income: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  total_equity: number | null;
}

/** 카테고리 → 추출 데이터 타입 매핑 */
export type ExtractedDataByCategory = {
  NDA: NdaExtractedData;
  LOI_MOU: LoiMouExtractedData;
  SPA_BTA: SpaBtaExtractedData;
  CORPORATE_DOCS: CorporateDocsExtractedData;
  TAX_FILING: TaxFilingExtractedData;
};

/** 카테고리별 추출 필드 라벨 */
export const FIELD_LABELS: Record<string, Record<string, string>> = {
  NDA: {
    counterparty_name: "상대방",
    nda_type: "NDA 유형",
    signed_at: "체결일",
    expires_at: "만료일",
    confidentiality_period_months: "비밀유지 기간(월)",
    jurisdiction: "관할법원",
  },
  LOI_MOU: {
    proposed_amount: "제안 인수가액",
    currency: "통화",
    valuation_method: "밸류에이션 방법",
    exclusivity_period_days: "배타적 협상기간(일)",
    conditions_precedent: "선행조건",
    valid_until: "유효기한",
    bid_type: "입찰 유형",
  },
  SPA_BTA: {
    final_purchase_price: "최종 매매대금",
    currency: "통화",
    closing_date: "거래종결일",
    counterparty_name: "상대방",
    effective_date: "효력 발생일",
    rw_cap_amount: "R&W 한도 금액",
    rw_cap_percentage: "R&W 한도 비율(%)",
    indemnification_period_months: "손해배상 청구기간(월)",
    contract_type: "계약 유형",
    key_conditions: "주요 선행조건",
    risk_summary: "리스크 요약",
  },
  CORPORATE_DOCS: {
    company_name: "상호",
    representative_name: "대표이사",
    establishment_date: "설립일",
    business_registration_number: "사업자등록번호",
    corporate_registration_number: "법인등록번호",
    capital_amount: "자본금의 액",
    total_shares_issued: "발행주식의 총수",
    par_value_per_share: "1주의 금액",
    common_shares: "보통주식 수",
    preferred_shares: "종류주식 수",
    business_type: "업태",
    business_item: "사업 목적",
    head_office_address: "본점",
    directors: "임원에 관한 사항",
    corporate_purpose: "목적사항",
  },
  REGISTRY_DOCS: {
    company_name: "상호",
    representative_name: "대표이사",
    establishment_date: "설립일",
    corporate_registration_number: "법인등록번호",
    capital_amount: "자본금의 액",
    total_shares_issued: "발행주식의 총수",
    par_value_per_share: "1주의 금액",
    common_shares: "보통주식 수",
    preferred_shares: "종류주식 수",
    head_office_address: "본점",
    directors: "임원에 관한 사항",
    corporate_purpose: "목적사항",
  },
  BIZ_REG_DOCS: {
    business_registration_number: "사업자등록번호",
    business_type: "업태",
    business_item: "종목",
  },
  TAX_FILING: {
    fiscal_year: "사업연도",
    revenue: "매출액",
    cost_of_goods_sold: "매출원가",
    gross_profit: "매출총이익",
    sga_expenses: "판매비와관리비",
    operating_income: "영업이익",
    non_operating_income: "영업외수익",
    non_operating_expenses: "영업외비용",
    income_before_tax: "법인세 차감전 순이익",
    corporate_tax: "법인세",
    net_income: "당기순이익",
    total_assets: "총자산",
    total_liabilities: "총부채",
    total_equity: "총자본",
  },
};
