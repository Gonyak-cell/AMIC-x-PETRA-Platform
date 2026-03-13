export type MarketingDocType = "TM" | "DM" | "IM";

export type MarketingDocStatus = "DRAFT" | "GENERATING" | "READY" | "FAILED";

export interface MarketingMaterial {
  id: string;
  transaction_id: string;
  doc_type: MarketingDocType;
  title: string;
  project_code: string | null;
  status: MarketingDocStatus;
  error_message: string | null;
  parameters: Record<string, unknown> | null;
  file_path: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  quality_score: number | null;
  quality_status: string | null;
  quality_issues: string[] | null;
  slide_count: number | null;
  distributed_to: string[] | null;
  distributed_at: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarketingMaterialCreate {
  doc_type: MarketingDocType;
  title: string;
  project_code?: string;
  parameters?: Record<string, unknown>;
}

export interface DistributionUpdate {
  distributed_to: string[];
  distributed_at?: string;
}

/** doc_type 한국어 라벨 */
export const MARKETING_DOC_LABELS: Record<MarketingDocType, string> = {
  TM: "Teaser Memo",
  DM: "Discussion Memo",
  IM: "Information Memo",
};

/** 상태 한국어 라벨 */
export const MARKETING_STATUS_LABELS: Record<MarketingDocStatus, string> = {
  DRAFT: "초안",
  GENERATING: "생성 중",
  READY: "완료",
  FAILED: "실패",
};

/** 품질 상태 라벨 */
export const QUALITY_STATUS_LABELS: Record<string, string> = {
  PASS: "통과",
  CONDITIONAL: "조건부",
  FAIL: "미통과",
  SKIPPED: "미검증",
  LEGACY_UNVERIFIED: "미검증",
};

/** 품질 상태 Badge variant 매핑 */
export const QUALITY_STATUS_VARIANT: Record<string, string> = {
  PASS: "success",
  CONDITIONAL: "warning",
  FAIL: "error",
  SKIPPED: "neutral",
  LEGACY_UNVERIFIED: "neutral",
};
