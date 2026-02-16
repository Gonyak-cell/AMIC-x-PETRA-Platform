export type ReportVersionStatus = "DRAFT" | "FINAL";
export type FileFormat = "pptx" | "docx" | "json";

export interface ReportVersion {
  id: string;
  deal_id: string;
  version: number;
  status: ReportVersionStatus;
  file_path: string | null;
  file_format: FileFormat;
  options: Record<string, boolean>;
  notes: string | null;
  created_by: string;
  created_at: string;
  finalized_at: string | null;
}

export interface ReportVersionCreate {
  file_format?: FileFormat;
  include_qoe?: boolean;
  include_nwc?: boolean;
  include_debt?: boolean;
  include_issues?: boolean;
  notes?: string | null;
}
