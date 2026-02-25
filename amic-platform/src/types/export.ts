export type ExportModule = "ma" | "docs" | "kiis";
export type ExportStatus = "pending" | "completed" | "failed" | "expired";
export type ExportFormat = "pdf" | "pptx" | "xlsx" | "csv" | "zip";

export interface ExportRecord {
  id: string;
  module: ExportModule;
  type: string;
  name: string;
  format: ExportFormat;
  file_size_bytes: number | null;
  status: ExportStatus;
  download_url: string | null;
  expires_at: string | null;
  created_at: string;
  created_by: string;
}

export interface ExportListParams {
  module?: ExportModule;
  status?: ExportStatus;
  page?: number;
  size?: number;
}

export interface PaginatedExports {
  items: ExportRecord[];
  total: number;
  page: number;
  size: number;
}
