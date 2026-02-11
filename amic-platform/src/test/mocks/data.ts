import type { Deal } from "@/modules/fdd/types/deal";
import type {
  Company,
  PaginatedResponse,
} from "@/modules/kiis/types/company";
import type { Document } from "@/modules/im/types/document";
import type { AuthUser } from "@/types/auth";

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
    current_phase: "MOU",
  },
];

// ── KIIS Fixtures ──

export const mockCompanies: PaginatedResponse<Company> = {
  items: [
    {
      corp_code: "00126380",
      corp_name: "삼성전자",
      stock_code: "005930",
      corp_cls: "Y",
      ceo_nm: "한종희",
      address: "경기도 수원시 영통구",
    },
    {
      corp_code: "00164779",
      corp_name: "SK하이닉스",
      stock_code: "000660",
      corp_cls: "Y",
      ceo_nm: "곽노정",
      address: "경기도 이천시",
    },
  ],
  total: 2,
  page: 1,
  size: 20,
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
      sections: ["overview", "financials", "valuation"],
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
      sections: ["overview", "financials"],
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
