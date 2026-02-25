export interface VdrOverviewItem {
  transaction_id: string;
  transaction_name: string;
  code_name: string;
  phase: string;
  status: string;
  vdr_initialized: boolean;
  total_folders: number;
  total_documents: number;
  total_size_bytes: number;
  last_upload_at: string | null;
}
