export type DisclosureType =
  | "annual_report"
  | "audit_report"
  | "quarterly"
  | "semi_annual"
  | "material"
  | "sanction"
  | "other";

export type DisclosureSource = "dart" | "kofia";

export interface DisclosureItem {
  id: number;
  report_nm: string;
  rcept_no: string;
  rcept_dt: string | null;
  disclosure_type: DisclosureType | null;
  dart_viewer_url: string | null;
  kofia_url: string | null;
  source: DisclosureSource;
}

export interface DisclosureListResponse {
  total: number;
  page: number;
  size: number;
  items: DisclosureItem[];
}

export interface DisclosureListParams {
  disclosure_type?: DisclosureType;
  page?: number;
  size?: number;
}

export interface DisclosureLinkResponse {
  rcept_no: string;
  dart_viewer_url: string | null;
  dart_pdf_url: string | null;
  kofia_url: string | null;
  report_nm: string;
  source: DisclosureSource;
}

export interface DisclosureSyncResponse {
  corp_code?: string;
  fund_code?: string;
  source: DisclosureSource;
  synced_count: number;
  skipped_count: number;
}
