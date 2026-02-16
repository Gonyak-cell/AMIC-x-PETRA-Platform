export type SourceType = "FILE" | "TB" | "GL" | "PDF";

export interface EvidenceLinkCreate {
  target_type: string;
  target_id: string;
  source_type: SourceType;
  source_id: string;
  source_detail?: Record<string, unknown> | null;
  transaction_id?: string | null;
  filter_hash?: string | null;
  engine_version?: string | null;
  snapshot_id?: string | null;
}

export interface EvidenceLinkRead {
  id: string;
  target_type: string;
  target_id: string;
  source_type: SourceType;
  source_id: string;
  source_detail: Record<string, unknown> | null;
  transaction_id: string | null;
  filter_hash: string | null;
  engine_version: string | null;
  deal_id: string;
  snapshot_id: string | null;
  created_at: string;
}

export interface EvidenceLinkBulkCreate {
  links: EvidenceLinkCreate[];
}
