import type { Page, Route } from "@playwright/test";

// ── Date Helpers (dynamic dates for 30d default range) ──

function daysAgo(n: number): string {
  return new Date(Date.now() - n * 86_400_000).toISOString();
}

function dateOnly(n: number): string {
  return new Date(Date.now() - n * 86_400_000).toISOString().slice(0, 10);
}

// ── Mock Data (mirrors src/test/mocks/data.ts) ──

export const mockUser = {
  id: "user-1",
  email: "admin@amic.co.kr",
  display_name: "Admin User",
  role: "ADMIN",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

export const mockDeals = [
  {
    id: "deal-1",
    name: "Project Alpha",
    deal_type: "COMPLETION_ACCOUNTS",
    base_currency: "KRW",
    reference_date: "2026-06-30",
    period_start: "2024-01-01",
    period_end: "2024-12-31",
    status: "ACTIVE",
    created_by: "user-1",
    created_at: "2026-01-15T09:00:00Z",
    updated_at: "2026-01-15T09:00:00Z",
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
    reference_date: "2026-03-31",
    period_start: "2024-01-01",
    period_end: "2024-12-31",
    status: "DRAFT",
    created_by: "user-1",
    created_at: "2026-02-01T10:00:00Z",
    updated_at: "2026-02-01T10:00:00Z",
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

export const mockCompanies = {
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

export const mockDashboardSummary = {
  counts: [
    { label: "기업", count: 150 },
    { label: "펀드", count: 45 },
    { label: "딜", count: 89 },
    { label: "리츠", count: 12 },
  ],
  recent_news_count: 15,
  recent_deals: [
    {
      target_company: "Target Inc",
      amount_display: "₩50B",
      sector: "IT",
      deal_date: "2026-02-10",
    },
  ],
  risk_companies: [
    {
      corp_code: "00126380",
      corp_name: "삼성전자",
      status_tag: "risk",
      total_score: 35,
    },
  ],
  data_freshness: [
    { entity: "Companies", count: 150, latest_at: "2026-02-10T08:00:00Z" },
    { entity: "Funds", count: 45, latest_at: "2026-02-09T12:00:00Z" },
  ],
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
  items: [
    { type: "company", id: "00126380", name: "삼성전자", description: "IT/반도체" },
    { type: "fund", id: "fund-1", name: "테스트펀드", description: null },
  ],
};

export const mockNewsList = {
  total: 3,
  page: 1,
  size: 20,
  items: [
    {
      id: 1,
      title: "삼성전자 반도체 실적 호조",
      source: "platum",
      author: "홍길동",
      published_at: "2026-02-10T09:00:00Z",
      url: "https://example.com/news/1",
      sentiment_score: 0.8,
    },
    {
      id: 2,
      title: "SK하이닉스 HBM 수주 확대",
      source: "dealsite",
      author: null,
      published_at: "2026-02-09T14:00:00Z",
      url: "https://example.com/news/2",
      sentiment_score: 0.6,
    },
    {
      id: 3,
      title: "바이오 산업 투자 동향 분석",
      source: "platum",
      author: "김분석",
      published_at: "2026-02-08T11:00:00Z",
      url: "https://example.com/news/3",
      sentiment_score: null,
    },
  ],
};

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
      created_at: "2026-02-01T09:00:00Z",
    },
    {
      id: 2,
      user_id: 1,
      company_id: 2,
      company_name: "SK하이닉스",
      alert_types: ["sanction", "reputation_change"],
      is_active: true,
      created_at: "2026-02-05T10:00:00Z",
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
      created_at: "2026-02-10T11:00:00Z",
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
      created_at: "2026-02-09T08:00:00Z",
    },
  ],
};

export const mockDocuments = {
  items: [
    {
      id: "doc-1",
      owner_id: "user-1",
      corp_code: "00126380",
      company_name: "삼성전자",
      project_name: "Samsung IM",
      im_style: "TITAN",
      sections: ["executive_summary", "financial_analysis", "valuation"],
      industry: "tech",
      status: "COMPLETED",
      progress_pct: 100,
      celery_task_id: null,
      pptx_path: "/files/doc-1.pptx",
      pdf_path: "/files/doc-1.pdf",
      file_size_bytes: 1024000,
      created_at: "2026-01-10T08:00:00Z",
      updated_at: "2026-01-10T09:00:00Z",
      completed_at: "2026-01-10T09:00:00Z",
    },
    {
      id: "doc-2",
      owner_id: "user-1",
      corp_code: "00164779",
      company_name: "SK하이닉스",
      project_name: "SK IM",
      im_style: "FULL",
      sections: ["executive_summary", "financial_analysis"],
      industry: "general",
      status: "GENERATING",
      progress_pct: 60,
      celery_task_id: "task-abc",
      pptx_path: null,
      pdf_path: null,
      file_size_bytes: null,
      created_at: "2026-02-01T10:00:00Z",
      updated_at: "2026-02-01T10:30:00Z",
      completed_at: null,
    },
  ],
  total: 2,
};

export const mockNotifications = [
  {
    id: "notif-1",
    module: "fdd",
    type: "deal_update",
    title: "Deal Status Changed",
    message: "Project Alpha moved to ACTIVE",
    is_read: false,
    created_at: "2026-02-01T10:00:00Z",
    link: "/fdd/deals/deal-1",
  },
  {
    id: "notif-2",
    module: "im",
    type: "document_complete",
    title: "IM Generation Complete",
    message: "Samsung IM document is ready for download",
    is_read: true,
    created_at: "2026-02-01T09:00:00Z",
    link: "/im/doc-1",
  },
];

export const mockExports = {
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
      expires_at: "2026-12-31T00:00:00Z",
      created_at: "2026-02-01T10:00:00Z",
      created_by: "user-1",
    },
  ],
  total: 1,
  page: 1,
  size: 20,
};

const mockAuditLogs = {
  total: 3,
  items: [
    {
      id: "audit-1",
      deal_id: null,
      entity_type: "deal",
      entity_id: "entity-1",
      action: "CREATE",
      actor: "user0@fdd.dev",
      old_value: null,
      new_value: null,
      user_id: "user-1",
      user_email: "user0@fdd.dev",
      user_role: "ADMIN",
      ip_address: "127.0.0.1",
      before_state: null,
      after_state: null,
      changed_fields: null,
      session_id: null,
      request_id: null,
      expires_at: null,
      created_at: "2026-02-01T10:00:00Z",
    },
  ],
  limit: 20,
  offset: 0,
};

// ── Helper to fulfill a route with JSON ──

function json(route: Route, data: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(data),
  });
}

// ── Bulk Mock Functions ──

/** Mock ALL API endpoints — makes tests fully deterministic without backends */
export async function mockAllApis(page: Page): Promise<void> {
  // Auth
  await page.route("**/api/fdd/auth/me", (route) => json(route, mockUser));
  await page.route("**/api/fdd/auth/users", (route) => json(route, []));

  // FDD
  await page.route("**/api/fdd/deals*", (route) => json(route, mockDeals));
  await page.route("**/api/fdd/health", (route) => json(route, { status: "ok" }));
  await page.route("**/api/fdd/notifications", (route) => json(route, mockNotifications));
  await page.route("**/api/fdd/exports*", (route) => json(route, mockExports));
  await page.route("**/api/fdd/audit-logs*", (route) => json(route, mockAuditLogs));

  // KIIS
  await page.route("**/api/kiis/companies*", (route) => json(route, mockCompanies));
  await page.route("**/api/kiis/alerts/unread-count", (route) => json(route, { count: 3 }));
  await page.route("**/api/kiis/alerts*", (route) => json(route, mockAlerts));
  await page.route("**/api/kiis/watchlist*", (route) => json(route, mockWatchlistItems));
  await page.route("**/api/kiis/news*", (route) => json(route, mockNewsList));
  await page.route("**/api/kiis/health", (route) => json(route, { status: "ok" }));
  await page.route("**/api/kiis/dashboard/summary", (route) => json(route, mockDashboardSummary));
  await page.route("**/api/kiis/search*", (route) => json(route, mockKiisSearchResults));
  await page.route("**/api/kiis/deals/by-sector*", (route) => json(route, mockSectorData));
  await page.route("**/api/kiis/deals/trends*", (route) => json(route, mockDealTrends));

  // IM
  await page.route("**/api/im/documents*", (route) => json(route, mockDocuments));
  await page.route("**/api/im/health", (route) => json(route, { status: "ok" }));
}

// ── Selective Mock Functions ──

/** Mock only FDD deals endpoint with custom data */
export async function mockFddDeals(page: Page, deals = mockDeals): Promise<void> {
  await page.route("**/api/fdd/deals*", (route) => json(route, deals));
}

/** Mock only KIIS companies endpoint with custom data */
export async function mockKiisCompanies(page: Page, companies = mockCompanies): Promise<void> {
  await page.route("**/api/kiis/companies*", (route) => json(route, companies));
}

/** Mock only IM documents endpoint with custom data */
export async function mockImDocuments(page: Page, documents = mockDocuments): Promise<void> {
  await page.route("**/api/im/documents*", (route) => json(route, documents));
}

/** Mock only search-related endpoints with custom data */
export async function mockSearchApis(
  page: Page,
  options?: {
    fddDeals?: typeof mockDeals;
    kiisResults?: typeof mockKiisSearchResults;
    imDocuments?: typeof mockDocuments;
  },
): Promise<void> {
  await page.route("**/api/fdd/deals*", (route) =>
    json(route, options?.fddDeals ?? mockDeals),
  );
  await page.route("**/api/kiis/search*", (route) =>
    json(route, options?.kiisResults ?? mockKiisSearchResults),
  );
  await page.route("**/api/im/documents*", (route) =>
    json(route, options?.imDocuments ?? mockDocuments),
  );
}

/** Mock health endpoints with optional error injection */
export async function mockHealthEndpoints(
  page: Page,
  overrides?: { fdd?: number; kiis?: number; im?: number },
): Promise<void> {
  const fddStatus = overrides?.fdd ?? 200;
  const kiisStatus = overrides?.kiis ?? 200;
  const imStatus = overrides?.im ?? 200;

  await page.route("**/api/fdd/health", (route) =>
    json(route, fddStatus === 200 ? { status: "ok" } : { detail: "error" }, fddStatus),
  );
  await page.route("**/api/kiis/health", (route) =>
    json(route, kiisStatus === 200 ? { status: "ok" } : { detail: "error" }, kiisStatus),
  );
  await page.route("**/api/im/health", (route) =>
    json(route, imStatus === 200 ? { status: "ok" } : { detail: "error" }, imStatus),
  );
}
