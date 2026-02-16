import type { Deal } from "@/modules/fdd/types/deal";
import type {
  Company,
  PaginatedResponse,
} from "@/modules/kiis/types/company";
import type { Document } from "@/modules/im/types/document";
import type { Company as ImCompany, DartIndustryString } from "@/modules/im/types/company";
import type { AuthUser } from "@/types/auth";
import type { NotificationItem } from "@/types/notification";
import type { PaginatedExports } from "@/types/export";

// ── Auth Fixtures ──

export const mockUser: AuthUser = {
  id: "user-1",
  email: "admin@amic.co.kr",
  display_name: "Admin User",
  role: "ADMIN",
  is_active: true,
  created_at: "2025-01-01T00:00:00Z",
};

export const mockViewerUser: AuthUser = {
  id: "user-2",
  email: "viewer@amic.co.kr",
  display_name: "Viewer User",
  role: "VIEWER",
  is_active: true,
  created_at: "2025-01-01T00:00:00Z",
};

// ── FDD Fixtures ──

export const mockDeals: Deal[] = [
  {
    id: "deal-1",
    name: "Project Alpha",
    deal_type: "COMPLETION_ACCOUNTS",
    base_currency: "KRW",
    reference_date: "2025-06-30",
    period_start: "2024-01-01",
    period_end: "2024-12-31",
    status: "ACTIVE",
    created_by: "user-1",
    created_at: "2025-01-15T09:00:00Z",
    updated_at: "2025-01-15T09:00:00Z",
    client_name: "Test Corp",
    client_contact_name: null,
    client_contact_email: null,
    target_company_name: "Target Inc",
    team_partner_id: null,
    team_manager_id: null,
    scope_qoe: true,
    scope_nwc: true,
    scope_debt: false,
    industry: "general",
    current_phase: "ANALYSIS",
  },
  {
    id: "deal-2",
    name: "Project Beta",
    deal_type: "LOCKED_BOX",
    base_currency: "USD",
    reference_date: "2025-03-31",
    period_start: "2024-01-01",
    period_end: "2024-12-31",
    status: "DRAFT",
    created_by: "user-1",
    created_at: "2025-02-01T10:00:00Z",
    updated_at: "2025-02-01T10:00:00Z",
    client_name: null,
    client_contact_name: null,
    client_contact_email: null,
    target_company_name: null,
    team_partner_id: null,
    team_manager_id: null,
    scope_qoe: true,
    scope_nwc: false,
    scope_debt: true,
    industry: "tech",
    current_phase: "MOU",
  },
];

// ── FDD Industries Fixtures ──

export const mockIndustries = [
  { id: "general", name_kr: "일반", name_en: "General" },
  { id: "tech", name_kr: "테크/SaaS", name_en: "Tech/SaaS" },
  { id: "healthcare", name_kr: "헬스케어", name_en: "Healthcare" },
  { id: "manufacturing", name_kr: "제조업", name_en: "Manufacturing" },
  { id: "financial_services", name_kr: "금융서비스", name_en: "Financial Services" },
  { id: "logistics", name_kr: "물류", name_en: "Logistics" },
];

export const mockDealSummary = {
  deal_id: "deal-1",
  deal_name: "Project Alpha",
  industry: "general",
  status: "ACTIVE",
  qoe: {
    reported_ebitda: "1000000000",
    adjusted_ebitda: "950000000",
    total_adjustments: "-50000000",
  },
  nwc: {
    net_working_capital: "500000000",
    peg_target: "450000000",
    peg_method: "average",
  },
  debt: null,
};

// ── KIIS Fixtures ──

export const mockCompanies: PaginatedResponse<Company> = {
  items: [
    {
      id: 1,
      corp_code: "00126380",
      corp_name: "삼성전자",
      stock_name: "삼성전자",
      stock_code: "005930",
      corp_cls: "Y",
    },
    {
      id: 2,
      corp_code: "00164779",
      corp_name: "SK하이닉스",
      stock_name: "SK하이닉스",
      stock_code: "000660",
      corp_cls: "Y",
    },
  ],
  total: 2,
  page: 1,
  size: 20,
};

// ── KIIS Dashboard Fixtures ──

export const mockDashboardSummary = {
  counts: [
    { label: "기업", count: 150 },
    { label: "펀드", count: 45 },
    { label: "딜", count: 89 },
    { label: "리츠", count: 12 },
  ],
  recent_news_count: 15,
  recent_deals: [],
  risk_companies: [],
  data_freshness: [],
};

export const mockSectorData = {
  items: [
    { sector: "IT", sector_name: "Information Technology", deal_count: 25, total_amount: "500000000000" },
    { sector: "BIO", sector_name: "Bio/Healthcare", deal_count: 18, total_amount: "300000000000" },
  ],
  total: 2,
};

export const mockDealTrends = {
  items: [
    { year: 2024, deal_count: 45, total_amount: "1000000000000" },
    { year: 2025, deal_count: 52, total_amount: "1200000000000" },
  ],
  total: 2,
};

export const mockKiisSearchResults = {
  total: 2,
  page: 1,
  size: 20,
  query: "삼성",
  items: [
    { index: "companies", id: "00126380", score: 1.5, source: { corp_name: "삼성전자", induty_code: "IT/반도체" } },
    { index: "funds", id: "fund-1", score: 1.2, source: { fund_name: "테스트펀드" } },
  ],
};

// ── KIIS Watchlist Fixtures ──

export const mockWatchlistItems = {
  total: 2,
  items: [
    {
      id: 1,
      user_id: 1,
      company_id: 1,
      company_name: "삼성전자",
      alert_types: ["news", "disclosure"],
      is_active: true,
      created_at: "2025-06-01T09:00:00Z",
    },
    {
      id: 2,
      user_id: 1,
      company_id: 2,
      company_name: "SK하이닉스",
      alert_types: ["sanction", "reputation_change"],
      is_active: true,
      created_at: "2025-06-05T10:00:00Z",
    },
  ],
};

export const mockAlerts = {
  total: 2,
  page: 1,
  size: 20,
  items: [
    {
      id: 101,
      alert_type: "news",
      title: "삼성전자 관련 뉴스",
      message: "삼성전자 실적 발표 관련 기사",
      is_read: false,
      company_id: 1,
      company_name: "삼성전자",
      reference_id: null,
      reference_type: null,
      created_at: "2025-06-10T11:00:00Z",
    },
    {
      id: 102,
      alert_type: "sanction",
      title: "SK하이닉스 제재 알림",
      message: null,
      is_read: true,
      company_id: 2,
      company_name: "SK하이닉스",
      reference_id: 50,
      reference_type: "sanction",
      created_at: "2025-06-09T08:00:00Z",
    },
  ],
};

// ── Notification Fixtures ──

export const mockNotifications: NotificationItem[] = [
  {
    id: "notif-1",
    module: "fdd",
    type: "deal_update",
    title: "Deal Status Changed",
    message: "Project Alpha moved to ACTIVE",
    is_read: false,
    created_at: new Date().toISOString(),
    link: "/fdd/deals/deal-1",
  },
  {
    id: "notif-2",
    module: "im",
    type: "document_complete",
    title: "IM Generation Complete",
    message: "Samsung IM document is ready for download",
    is_read: true,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    link: "/im/doc-1",
  },
];

// ── Export Fixtures ──

export const mockExports: PaginatedExports = {
  items: [
    {
      id: "export-1",
      module: "fdd",
      type: "deal_report",
      name: "Project Alpha Report",
      format: "pdf",
      file_size_bytes: 2048000,
      status: "completed",
      download_url: "/api/fdd/exports/export-1/download",
      expires_at: new Date(Date.now() + 30 * 86400000).toISOString(),
      created_at: new Date().toISOString(),
      created_by: "user-1",
    },
  ],
  total: 1,
  page: 1,
  size: 20,
};

// ── IM Company Fixtures ──

export const mockImCompany: ImCompany = {
  id: "im-company-1",
  corp_code: "00126380",
  corp_name: "삼성전자",
  corp_name_en: "Samsung Electronics",
  stock_code: "005930",
  industry: "소프트웨어" as DartIndustryString,
  homepage_url: "https://www.samsung.com",
  fetch_status: "COMPLETED",
  last_fetched_at: "2025-01-10T08:00:00Z",
  cache_expires_at: "2025-02-10T08:00:00Z",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-10T08:00:00Z",
};

// ── IM Fixtures ──

export const mockDocuments: { items: Document[]; total: number } = {
  items: [
    {
      id: "doc-1",
      owner_id: "user-1",
      corp_code: "00126380",
      company_name: "삼성전자",
      project_name: "Samsung IM",
      im_style: "TITAN",
      sections: [
        "cover", "disclaimer", "toc_divider", "executive_summary",
        "investment_highlights", "market_overview", "business_overview",
        "financial_analysis", "contact",
      ],
      industry: "tech",
      status: "COMPLETED",
      progress_pct: 100,
      celery_task_id: null,
      pptx_path: "/files/doc-1.pptx",
      pdf_path: "/files/doc-1.pdf",
      file_size_bytes: 1024000,
      created_at: "2025-01-10T08:00:00Z",
      updated_at: "2025-01-10T09:00:00Z",
      completed_at: "2025-01-10T09:00:00Z",
    },
    {
      id: "doc-2",
      owner_id: "user-1",
      corp_code: "00164779",
      company_name: "SK하이닉스",
      project_name: "SK IM",
      im_style: "FULL",
      sections: [],
      industry: "general",
      status: "GENERATING",
      progress_pct: 60,
      celery_task_id: "task-abc",
      pptx_path: null,
      pdf_path: null,
      file_size_bytes: null,
      created_at: "2025-02-01T10:00:00Z",
      updated_at: "2025-02-01T10:30:00Z",
      completed_at: null,
    },
  ],
  total: 2,
};
