// NDA 마크업 버전 타입

export interface NdaMarkup {
  id: string;
  nda_id: string;
  version_label: string;
  version_number: number;
  version_date: string;
  source_party: string | null;
  markup_type: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  changes_summary: string | null;
  key_changes: unknown[] | null;
  redline_issues_count: number | null;
  base_version_id: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
  has_file: boolean;
  has_redline: boolean;
}

export interface NdaMarkupListResponse {
  items: NdaMarkup[];
  total: number;
  limit: number;
  offset: number;
}
