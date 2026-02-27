// 협상 워크스페이스 전용 타입

export interface NegotiationGanttItem {
  contract_id: string;
  contract_type: string;
  title: string;
  status: string;
  total_markups: number;
  open_issues: number;
  first_markup_at: string | null;
  latest_markup_at: string | null;
  created_at: string | null;
}

export interface NegotiationGanttData {
  items: NegotiationGanttItem[];
  transaction_start_date: string | null;
  target_close_date: string | null;
}

export interface MarkupComparison {
  version_a: number;
  version_b: number;
  markup_a_label: string | null;
  markup_b_label: string | null;
  markup_a_party: string | null;
  markup_b_party: string | null;
  markup_a_summary: string | null;
  markup_b_summary: string | null;
  key_changes_a: string[] | null;
  key_changes_b: string[] | null;
  additions: string[];
  deletions: string[];
  common: string[];
}
