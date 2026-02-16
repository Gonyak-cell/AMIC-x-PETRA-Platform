export type ReportVersionStatus = "DRAFT" | "FINAL";

export interface ReportVersion {
  id: string;
  deal_id: string;
  version: number;
  status: ReportVersionStatus;
  file_path: string | null;
  file_format: string;
  options: Record<string, boolean>;
  notes: string | null;
  created_by: string;
  created_at: string;
  finalized_at: string | null;
}
