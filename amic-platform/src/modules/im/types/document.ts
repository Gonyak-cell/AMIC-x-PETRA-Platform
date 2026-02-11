export type IMStyle = "TITAN" | "COVENANT" | "FULL" | "CUSTOM";

export type DocumentStatus =
  | "PENDING"
  | "COLLECTING"
  | "ANALYZING"
  | "GENERATING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export interface Document {
  id: string;
  owner_id: string;
  corp_code: string;
  company_name: string;
  project_name: string | null;
  im_style: IMStyle;
  sections: string[];
  status: DocumentStatus;
  progress_pct: number;
  celery_task_id: string | null;
  pptx_path: string | null;
  pdf_path: string | null;
  file_size_bytes: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface DocumentCreate {
  corp_code: string;
  project_name?: string;
  im_style: IMStyle;
  sections?: string[];
  industry?: string;
  webhook_url?: string;
  pdf_password?: string;
}

export interface DocumentListParams {
  offset?: number;
  limit?: number;
}
