import type { IndustryId } from "@/types/industry";

/** Document type — frontend-only concept distinguishing TM, IM, and FDD. */
export type DocumentType = "teaser" | "im" | "fdd";

export type IMStyle = "TITAN" | "COVENANT" | "FULL" | "TEASER" | "CUSTOM";
export type DataSource = "DART" | "MANUAL" | "EXCEL";

/** PPT 디자인 스타일 — IM/TM 문서 생성 시 브랜딩 선택. */
export type PPTDesignStyle = "AMIC" | "AMIC_COLLAB";

export type { IndustryId };

export type DocumentStatus =
  | "PENDING"
  | "COLLECTING"
  | "ANALYZING"
  | "GENERATING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

/** Valid backend section IDs (IM + TM sections). */
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
  | "industry_overview"
  // TM (Teaser Memorandum) sections
  | "target_positioning"
  | "market_outlook"
  | "demand_driver"
  | "supply_driver"
  | "target_overview"
  | "target_highlights"
  | "proforma_plan"
  | "proforma_financials";

/** Structural sections always included — not user-toggleable. */
export const STRUCTURAL_SECTIONS: SectionId[] = [
  "cover",
  "disclaimer",
  "toc_divider",
  "contact",
];

/**
 * Content sections users can toggle in CUSTOM IM mode.
 * TM (Teaser) sections are excluded — TM uses a fixed 4-group structure
 * and does not support CUSTOM section selection.
 */
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

/** snake_case section ID to human-readable label. */
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
  // TM sections
  target_positioning: "Target Positioning",
  market_outlook: "Market Outlook",
  demand_driver: "Key Demand Driver",
  supply_driver: "Key Supply Driver",
  target_overview: "Target Overview",
  target_highlights: "Target Highlights",
  proforma_plan: "Pro-Forma Plan",
  proforma_financials: "Pro-Forma Financials",
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
  webhook_url?: string;
  pdf_password?: string;
  /** PPT 디자인 스타일. 미지정 시 백엔드 기본값 "AMIC" 적용. */
  ppt_design_style?: PPTDesignStyle;
  /** AMIC_COLLAB 선택 시 필수. e.g. "삼일PwC", "Goldman Sachs" */
  collab_partner_name?: string;
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

const IM_STYLES = ["TITAN", "COVENANT", "FULL", "TEASER", "CUSTOM"] as const;

export function isIMStyle(value: string): value is IMStyle {
  return (IM_STYLES as readonly string[]).includes(value);
}

/** Infer document type from IM style. */
export function getDocumentType(style: IMStyle): DocumentType {
  return style === "TEASER" ? "teaser" : "im";
}
