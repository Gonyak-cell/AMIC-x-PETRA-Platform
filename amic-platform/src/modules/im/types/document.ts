import type { IndustryId } from "@/types/industry";

export type IMStyle = "TITAN" | "COVENANT" | "FULL" | "CUSTOM";
export type DataSource = "DART" | "MANUAL" | "EXCEL";

// Re-export shared IndustryId from common types
export type { IndustryId };

export type DocumentStatus =
  | "PENDING"
  | "COLLECTING"
  | "ANALYZING"
  | "GENERATING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

/** Valid backend section IDs (matches im_document.py SECTION_IDS + INDUSTRY_SECTION_IDS). */
export type SectionId =
  | "cover"
  | "disclaimer"
  | "toc_divider"
  | "deal_overview"
  | "executive_summary"
  | "investment_highlights"
  | "company_overview"
  | "business_model"
  | "market_overview"
  | "business_overview"
  | "value_creation"
  | "growth_strategy"
  | "financial_analysis"
  | "valuation"
  | "management_team"
  | "shareholder_structure"
  | "transaction_structure"
  | "appendix"
  | "contact"
  | "industry_kpi"
  | "industry_overview";

/** Structural sections always included — not user-toggleable. */
export const STRUCTURAL_SECTIONS: SectionId[] = [
  "cover",
  "disclaimer",
  "toc_divider",
  "contact",
];

/** Content sections users can toggle in CUSTOM mode. */
export const CONTENT_SECTIONS: { id: SectionId; label: string }[] = [
  { id: "deal_overview", label: "Deal Overview" },
  { id: "executive_summary", label: "Executive Summary" },
  { id: "investment_highlights", label: "Investment Highlights" },
  { id: "company_overview", label: "Company Overview" },
  { id: "business_model", label: "Business Model" },
  { id: "market_overview", label: "Market Overview" },
  { id: "business_overview", label: "Business Overview" },
  { id: "value_creation", label: "Value Creation" },
  { id: "growth_strategy", label: "Growth Strategy" },
  { id: "financial_analysis", label: "Financial Analysis" },
  { id: "valuation", label: "Valuation" },
  { id: "management_team", label: "Management Team" },
  { id: "shareholder_structure", label: "Shareholder Structure" },
  { id: "transaction_structure", label: "Transaction Structure" },
  { id: "appendix", label: "Appendix" },
  { id: "industry_kpi", label: "Industry KPIs" },
  { id: "industry_overview", label: "Industry Overview" },
];

/** snake_case section ID → human-readable label. */
export const SECTION_LABEL_MAP: Record<SectionId, string> = {
  cover: "Cover",
  disclaimer: "Disclaimer",
  toc_divider: "Table of Contents",
  deal_overview: "Deal Overview",
  executive_summary: "Executive Summary",
  investment_highlights: "Investment Highlights",
  company_overview: "Company Overview",
  business_model: "Business Model",
  market_overview: "Market Overview",
  business_overview: "Business Overview",
  value_creation: "Value Creation",
  growth_strategy: "Growth Strategy",
  financial_analysis: "Financial Analysis",
  valuation: "Valuation",
  management_team: "Management Team",
  shareholder_structure: "Shareholder Structure",
  transaction_structure: "Transaction Structure",
  appendix: "Appendix",
  contact: "Contact",
  industry_kpi: "Industry KPIs",
  industry_overview: "Industry Overview",
};

export interface Document {
  id: string;
  owner_id: string;
  corp_code: string | null;
  company_name: string;
  project_name: string | null;
  data_source: DataSource;
  im_style: IMStyle;
  sections: SectionId[];
  industry: IndustryId | null;
  status: DocumentStatus;
  progress_pct: number;
  celery_task_id: string | null;
  pptx_path: string | null;
  pdf_path: string | null;
  file_size_bytes: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface DocumentCreate {
  company_name: string;
  project_name: string;
  corp_code?: string;
  data_source?: DataSource;
  im_style: IMStyle;
  sections?: SectionId[];
  industry?: IndustryId;
  /** Backend supports webhook notifications on completion. Not exposed in UI (internal/API-only use). */
  webhook_url?: string;
  pdf_password?: string;
}

export interface DocumentListParams {
  offset?: number;
  limit?: number;
  search?: string;
}

/** Statuses indicating the document is still being processed. */
export const IN_PROGRESS_STATUSES: DocumentStatus[] = [
  "PENDING",
  "COLLECTING",
  "ANALYZING",
  "GENERATING",
  "RENDERING",
];

const IM_STYLES = ["TITAN", "COVENANT", "FULL", "CUSTOM"] as const;

export function isIMStyle(value: string): value is IMStyle {
  return (IM_STYLES as readonly string[]).includes(value);
}
