// ── VDR 폴더 ─────────────────────────────────────────────

export type VdrFolderCategory =
  | "CORPORATE"
  | "FINANCIAL"
  | "LEGAL"
  | "TAX"
  | "HR"
  | "TECHNICAL"
  | "COMMERCIAL"
  | "REAL_ESTATE"
  | "ENVIRONMENT"
  | "IP"
  | "INSURANCE"
  | "MARKET_RESEARCH"
  | "CUSTOM";

/**
 * 서버는 중첩 트리(children 배열)로 응답하지만,
 * useVdrFolders 훅이 flattenVdrFolders로 평탄화하여 parent_id 참조 배열로 변환한다.
 * UI 컴포넌트는 평탄 배열을 받아 childrenByParentId Map으로 인덱싱해 사용한다.
 */
export interface VdrFolder {
  id: string;
  transaction_id: string;
  parent_id: string | null;
  name: string;
  category: VdrFolderCategory;
  order_index: number;
  is_required: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
  children: VdrFolder[];
  document_count: number;
}

export interface VdrFolderCreate {
  name: string;
  category?: VdrFolderCategory;
  parent_id?: string;
  description?: string;
}

export interface VdrFolderUpdate {
  name?: string;
  order_index?: number;
  description?: string;
}

// ── VDR 문서 ─────────────────────────────────────────────

export type VdrDocumentStatus = "ACTIVE" | "ARCHIVED" | "DELETED";

export type VdrClassificationStatus =
  | "DIRECT"
  | "PENDING_REVIEW"
  | "CLASSIFIED"
  | "MANUAL_REVIEW"
  | "MANUAL";

export interface VdrDocument {
  id: string;
  transaction_id: string;
  folder_id: string;
  original_name: string;
  file_size_bytes: number;
  mime_type: string;
  sha256_hash: string | null;
  status: VdrDocumentStatus;
  description: string | null;
  uploaded_by_email: string | null;
  classification_status: VdrClassificationStatus | null;
  classification_score: number | null;
  manual_review_needed: boolean;
  created_at: string;
  updated_at: string;
}

export interface VdrDocumentUpdate {
  description?: string;
  folder_id?: string;
}

export type VdrWorkstream = "LDD" | "FDD" | "VALUATION" | "COMMON";
export type VdrRoutingQueueStatus = "open" | "reviewed" | "all";

export interface VdrRoutingOverride {
  id: string;
  transaction_id: string;
  vdr_document_id: string;
  primary_workstream: VdrWorkstream;
  workstream_tags: VdrWorkstream[];
  override_note: string | null;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VdrRoutingOverrideUpsert {
  primary_workstream: VdrWorkstream;
  workstream_tags?: VdrWorkstream[];
  override_note?: string | null;
}

export interface VdrRoutingDecision {
  primary_workstream: VdrWorkstream;
  workstream_tags: VdrWorkstream[];
  confidence: number;
  requires_manual_review: boolean;
  reasons: string[];
  is_override: boolean;
  override_note: string | null;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
}

export interface VdrRoutingQueueItem {
  document: VdrDocument;
  folder_name: string;
  folder_category: VdrFolderCategory;
  routing_status: "OPEN_REVIEW" | "OVERRIDDEN" | "AUTO_ROUTED";
  auto_route: VdrRoutingDecision;
  effective_route: VdrRoutingDecision;
}

export interface VdrRoutingQueueSummary {
  total_documents: number;
  returned_documents: number;
  open_documents: number;
  reviewed_documents: number;
  auto_routed_documents: number;
  by_effective_workstream: Partial<Record<VdrWorkstream, number>>;
}

export interface VdrRoutingQueueResponse {
  summary: VdrRoutingQueueSummary;
  items: VdrRoutingQueueItem[];
}

// ── Direct Upload ────────────────────────────────────────

export interface DirectUploadFileResult {
  document: VdrDocument;
  routed_folder: VdrFolder;
  routed_category: VdrFolderCategory | null;
  classification_status: VdrClassificationStatus;
  score: number;
  was_fallback: boolean;
}

export interface FailedFileInfo {
  filename: string;
  reason: string;
}

export interface DirectUploadBatchResult {
  results: DirectUploadFileResult[];
  pending_review_count: number;
  total_uploaded: number;
  failed_files: FailedFileInfo[];
}

export interface ClassificationStatusItem {
  document_id: string;
  classification_status: VdrClassificationStatus;
  routed_folder: VdrFolder | null;
  routed_category: VdrFolderCategory | null;
  manual_review_needed: boolean;
}

// ── VDR 요약 ─────────────────────────────────────────────

export interface VdrSummary {
  total_folders: number;
  total_documents: number;
  total_size_bytes: number;
  initialized: boolean;
}

// ── 상수 ─────────────────────────────────────────────────

export const VDR_CATEGORY_LABELS: Record<VdrFolderCategory, string> = {
  CORPORATE: "기업 일반",
  FINANCIAL: "재무 자료",
  LEGAL: "법률 자료",
  TAX: "세무 자료",
  HR: "인사/노무",
  TECHNICAL: "기술/IT",
  COMMERCIAL: "영업/마케팅",
  REAL_ESTATE: "부동산/자산",
  ENVIRONMENT: "환경",
  IP: "지식재산권",
  INSURANCE: "보험",
  MARKET_RESEARCH: "시장자료",
  CUSTOM: "사용자 정의",
};

export const VDR_WORKSTREAM_LABELS: Record<VdrWorkstream, string> = {
  LDD: "LDD",
  FDD: "FDD",
  VALUATION: "Valuation",
  COMMON: "Common",
};

export const MIME_TYPE_LABELS: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "Word",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation":
    "PPT",
  "image/png": "PNG",
  "image/jpeg": "JPEG",
  "text/csv": "CSV",
  "text/plain": "TXT",
  "application/zip": "ZIP",
};

/** 2차 심사 상태 폴링 간격 (ms) */
export const CLASSIFICATION_POLL_INTERVAL_MS = 5000;

// ── VDR 접근 추적 ────────────────────────────────────────
export type VdrAccessAction = "VIEW" | "DOWNLOAD" | "UPLOAD";

export interface VdrAccessLog {
  id: string;
  transaction_id: string;
  document_id: string | null;
  folder_id: string | null;
  user_email: string;
  user_id: string;
  action: VdrAccessAction;
  ip_address: string | null;
  user_agent: string | null;
  buyer_id: string | null;
  created_at: string;
}

export interface VdrAccessLogListResponse {
  items: VdrAccessLog[];
  total: number;
}

export interface BuyerActivitySummary {
  buyer_id: string;
  buyer_name: string;
  unique_documents_accessed: number;
  total_views: number;
  total_downloads: number;
  last_access_at: string | null;
}

/** VDR 파일 업로드 제약 조건 — 백엔드와 동기화 필수 */
export const VDR_CONSTRAINTS = {
  /** 최대 파일 크기 (bytes): 100MB */
  MAX_FILE_SIZE: 100 * 1024 * 1024,
  /** 최대 파일 크기 (표시용) */
  MAX_FILE_SIZE_LABEL: "100MB",
  /** 허용 MIME 타입 — deal-mgmt/app/routers/vdr.py _ALLOWED_MIME_TYPES 동기화 */
  ALLOWED_MIME_TYPES: new Set([
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "image/png",
    "image/jpeg",
    "text/plain",
    "text/csv",
    "application/zip",
    // M&A 실사 특화 포맷 (BE와 동기화)
    "application/haansofthwp", // .hwp
    "application/x-hwp", // .hwp 변형
    "image/vnd.dwg", // .dwg
    "application/dxf", // .dxf
    "application/x-tar", // .tar
    "application/gzip", // .gz
    "application/json", // .json
    "application/vnd.google-earth.kml+xml", // .kml
    "application/x-iwork-keynote-sffkey", // .key
    "message/rfc822", // .eml
    "application/vnd.ms-outlook", // .msg
  ]),
  /** 허용 파일 확장자 (input accept 속성용) — BE와 동기화 */
  ACCEPT_EXTENSIONS:
    ".pdf,.docx,.xlsx,.pptx,.doc,.xls,.ppt,.png,.jpg,.jpeg,.txt,.csv,.zip,.hwp,.dwg,.dxf,.tar,.gz,.json,.kml,.key,.eml,.msg",
} as const;
