// 문서 버전 관리 타입 — DocumentMaster + DocumentRevision

export type DocumentType =
  | "CONTRACT_SPA"
  | "CONTRACT_AMENDMENT"
  | "CONTRACT_SIDE_LETTER"
  | "CONTRACT_SHA"
  | "CONTRACT_ESCROW"
  | "CONTRACT_BTA"
  | "CONTRACT_SSA"
  | "CONTRACT_OTHER"
  | "NDA"
  | "RFI_EXCEL"
  | "MEETING_MINUTES"
  | "DD_REPORT"
  | "OTHER";

export type UploadSource =
  | "MANUAL"
  | "CONTRACT_MARKUP"
  | "NDA_MARKUP"
  | "RFI_IMPORT"
  | "SYSTEM";

export interface DocumentMaster {
  id: string;
  transaction_id: string;
  doc_type: DocumentType;
  doc_name: string;
  description: string | null;
  current_revision_number: number;
  is_archived: boolean;
  contract_id: string | null;
  nda_id: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentMasterListResponse {
  items: DocumentMaster[];
  total: number;
}

export interface DocumentRevision {
  id: string;
  document_id: string;
  revision_number: number;
  sha256_hash: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string | null;
  uploaded_by_email: string | null;
  upload_source: UploadSource;
  changes_summary: string | null;
  prev_revision_id: string | null;
  is_current: boolean;
  is_deleted: boolean;
  source_entity_type: string | null;
  source_entity_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RevisionListResponse {
  items: DocumentRevision[];
  total: number;
}

export interface DocumentMasterCreatePayload {
  doc_type: DocumentType;
  doc_name: string;
  description?: string | null;
  contract_id?: string | null;
  nda_id?: string | null;
}
