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
  created_at: string;
  updated_at: string;
}

export interface VdrDocumentUpdate {
  description?: string;
  folder_id?: string;
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

/** VDR 파일 업로드 제약 조건 — 백엔드와 동기화 필수 */
export const VDR_CONSTRAINTS = {
  /** 최대 파일 크기 (bytes): 100MB */
  MAX_FILE_SIZE: 100 * 1024 * 1024,
  /** 최대 파일 크기 (표시용) */
  MAX_FILE_SIZE_LABEL: "100MB",
  /** 허용 MIME 타입 */
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
  ]),
  /** 허용 파일 확장자 (input accept 속성용) */
  ACCEPT_EXTENSIONS:
    ".pdf,.docx,.xlsx,.pptx,.doc,.xls,.ppt,.png,.jpg,.jpeg,.txt,.csv,.zip",
} as const;
