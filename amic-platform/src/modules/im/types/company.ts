export type CompanyFetchStatus = "PENDING" | "REFRESHING" | "COMPLETED" | "FAILED";

/**
 * Raw DART industry string (e.g. "소프트웨어", "금융업").
 * NOT the same as IndustryId — must be mapped via DART_INDUSTRY_MAP in CreateDocumentPage.
 */
export type DartIndustryString = string & { readonly __brand: "DartIndustryString" };

export interface Company {
  id: string;
  corp_code: string;
  corp_name: string;
  corp_name_en: string | null;
  stock_code: string | null;
  /** Raw DART industry string — use DART_INDUSTRY_MAP to convert to IndustryId. */
  industry: DartIndustryString | null;
  homepage_url: string | null;
  fetch_status: CompanyFetchStatus;
  last_fetched_at: string | null;
  cache_expires_at: string | null;
  created_at: string;
  updated_at: string;
}
