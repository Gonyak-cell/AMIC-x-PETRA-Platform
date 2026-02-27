// 계약 마크업 버전 타입

export interface ContractMarkup {
  id: string;
  contract_id: string;
  meeting_id: string | null;
  version_label: string;
  version_number: number;
  source_party: string | null;
  markup_type: string | null;
  file_path: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  changes_summary: string | null;
  key_changes: string[] | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractMarkupListResponse {
  items: ContractMarkup[];
  total: number;
}
