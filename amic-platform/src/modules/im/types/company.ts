export type CompanyFetchStatus = "PENDING" | "COLLECTING" | "COMPLETED" | "FAILED";

export interface Company {
  id: string;
  corp_code: string;
  corp_name: string;
  corp_name_en: string | null;
  stock_code: string | null;
  industry: string | null;
  homepage_url: string | null;
  fetch_status: CompanyFetchStatus;
  last_fetched_at: string | null;
  cache_expires_at: string | null;
  created_at: string;
  updated_at: string;
}
