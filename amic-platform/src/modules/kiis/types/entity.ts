export interface EntityMatchItem {
  corp_code: string;
  corp_name: string;
  similarity: number;
  matched_by: string | null;
}

export interface EntityResolveRequest {
  name: string;
  threshold?: number;
  max_candidates?: number;
}

export interface EntityResolveResponse {
  query: string;
  normalized: string;
  match: EntityMatchItem | null;
  candidates: EntityMatchItem[];
}

export interface AliasItem {
  id: number;
  alias_name: string;
  company_id: number;
  is_manual: boolean;
  corp_code: string | null;
  corp_name: string | null;
}

export interface AliasCreateRequest {
  alias_name: string;
  corp_code: string;
}

export interface AliasListResponse {
  total: number;
  items: AliasItem[];
}

export interface AliasListParams {
  corp_code?: string;
}
