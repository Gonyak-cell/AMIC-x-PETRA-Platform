export type CompanyFetchStatus = "PENDING" | "REFRESHING" | "COMPLETED" | "FAILED";

export type DartIndustryString = string & { readonly __brand: "DartIndustryString" };

export interface Company {
  id: string;
  corp_code: string;
  corp_name: string;
  corp_name_en: string | null;
  stock_code: string | null;
  industry: DartIndustryString | null;
  homepage_url: string | null;
  fetch_status: CompanyFetchStatus;
  last_fetched_at: string | null;
  cache_expires_at: string | null;
  created_at: string;
  updated_at: string;
}
