/** 범용 첨부파일 타입. */

/** VDR 자동 연동 결과 정보. */
export interface VdrSyncInfo {
  vdr_document_id: string;
  folder_name: string;
  category: string | null;
  classification_status: string;
}

export type AttachmentProcessingStatus =
  | "PENDING"
  | "RUNNING"
  | "SYNCED"
  | "FAILED"
  | "SKIPPED";

export interface Attachment {
  id: string;
  transaction_id: string;
  entity_type: AttachmentEntityType;
  entity_id: string | null;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  processing_status: AttachmentProcessingStatus;
  processing_error: string | null;
  description: string | null;
  uploaded_by_email: string | null;
  created_at: string;
  updated_at: string;
  vdr_sync?: VdrSyncInfo | null;
}

export interface AttachmentListResponse {
  items: Attachment[];
  total: number;
}

export type AttachmentEntityType =
  | "ENGAGEMENT"
  | "MARKETING_MATERIAL"
  | "FINANCIAL_MODEL"
  | "NDA"
  | "BID"
  | "DD_CHECKLIST"
  | "CONTRACT"
  | "CLOSING"
  | "PMI"
  | "EARNOUT"
  | "MARKETING_LOG"
  | "MILESTONE";

/** 탭 ID → entity_type 매핑. */
export const TAB_ENTITY_TYPE_MAP: Record<string, AttachmentEntityType> = {
  engagements: "ENGAGEMENT",
  "marketing-materials": "MARKETING_MATERIAL",
  models: "FINANCIAL_MODEL",
  ndas: "NDA",
  bids: "BID",
  "dd-checklist": "DD_CHECKLIST",
  contracts: "CONTRACT",
  closing: "CLOSING",
  pmi: "PMI",
  earnout: "EARNOUT",
};

/** 업로드 제약 상수 (백엔드와 동기화). */
export const ATTACHMENT_CONSTRAINTS = {
  MAX_FILE_SIZE: 50 * 1024 * 1024,
  MAX_FILE_SIZE_LABEL: "50MB",
  ALLOWED_EXTENSIONS: new Set([
    ".docx",
    ".doc",
    ".pdf",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".hwp",
    ".hwpx",
    ".txt",
    ".csv",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".aac",
    ".wma",
    ".flac",
  ]),
  ACCEPT_EXTENSIONS:
    ".docx,.doc,.pdf,.xlsx,.xls,.pptx,.ppt,.hwp,.hwpx,.txt,.csv,.zip,.png,.jpg,.jpeg,.mp3,.wav,.m4a,.ogg,.aac,.wma,.flac",
};

/** MIME 타입 → 라벨 매핑. */
export const ATTACHMENT_MIME_LABELS: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "DOCX",
  "application/msword": "DOC",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
  "application/vnd.ms-excel": "XLS",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation":
    "PPTX",
  "application/vnd.ms-powerpoint": "PPT",
  "application/vnd.hancom.hwp": "HWP",
  "text/plain": "TXT",
  "text/csv": "CSV",
  "application/zip": "ZIP",
  "image/png": "PNG",
  "image/jpeg": "JPEG",
  "audio/mpeg": "MP3",
  "audio/wav": "WAV",
  "audio/x-m4a": "M4A",
  "audio/ogg": "OGG",
  "audio/aac": "AAC",
  "audio/x-ms-wma": "WMA",
  "audio/flac": "FLAC",
};
