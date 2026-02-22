import { http, HttpResponse, passthrough } from "msw";
import {
  mockDeals,
  mockCompanies,
  mockDocuments,
  mockDashboardSummary,
  mockSectorData,
  mockDealTrends,
  mockKiisSearchResults,
  mockWatchlistItems,
  mockAlerts,
  mockNotifications,
  mockExports,
  mockIndustries,
  mockDealSummary,
  mockImCompany,
  SEED_ACCOUNTS,
} from "./data";
import type { AuthUser } from "@/types/auth";

// MSW 인증 상태 (httpOnly 쿠키 시뮬레이션)
// 실제 백엔드는 Set-Cookie 헤더로 토큰 관리하지만,
// MSW에서는 쿠키를 설정/확인할 수 없으므로 sessionStorage로 추적
// sessionStorage: HMR 업데이트에도 상태 유지, 탭 닫으면 초기화
const MSW_AUTH_KEY = "msw-authenticated";
const MSW_USER_KEY = "msw-current-user";

function getMswCurrentUser(): AuthUser | null {
  const json = sessionStorage.getItem(MSW_USER_KEY);
  if (!json) return null;
  try { return JSON.parse(json); } catch { return null; }
}

function setMswSession(user: AuthUser | null): void {
  if (user) {
    sessionStorage.setItem(MSW_AUTH_KEY, "true");
    sessionStorage.setItem(MSW_USER_KEY, JSON.stringify(user));
  } else {
    sessionStorage.removeItem(MSW_AUTH_KEY);
    sessionStorage.removeItem(MSW_USER_KEY);
  }
}

function isMswAuthenticated(): boolean {
  return sessionStorage.getItem(MSW_AUTH_KEY) === "true";
}

export const handlers = [
  // ── Auth (httpOnly cookie 기반 — 시드 계정 검증) ──
  http.post("*/api/fdd/auth/login", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    const account = SEED_ACCOUNTS.find(
      (a) => a.email === body.email && a.password === body.password,
    );
    if (!account) {
      return HttpResponse.json(
        { detail: "Invalid email or password" },
        { status: 401 },
      );
    }
    setMswSession(account.user);
    return HttpResponse.json({ message: "Login successful" });
  }),

  http.post("*/api/fdd/auth/logout", () => {
    setMswSession(null);
    return HttpResponse.json({ message: "Logged out" });
  }),

  http.post("*/api/fdd/auth/refresh", () => {
    if (!isMswAuthenticated()) {
      return new HttpResponse(null, { status: 401 });
    }
    return HttpResponse.json({ message: "Token refreshed" });
  }),

  http.get("*/api/fdd/auth/me", () => {
    const user = getMswCurrentUser();
    if (!isMswAuthenticated() || !user) {
      return new HttpResponse(null, { status: 401 });
    }
    return HttpResponse.json(user);
  }),

  http.get("*/api/fdd/auth/users", () => {
    return HttpResponse.json(SEED_ACCOUNTS.map((a) => a.user));
  }),

  // ── FDD Deals ──
  http.get("*/api/fdd/deals", () => {
    return HttpResponse.json(mockDeals);
  }),

  http.get("*/api/fdd/deals/:dealId", ({ params }) => {
    const deal = mockDeals.find((d) => d.id === params.dealId);
    if (!deal) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(deal);
  }),

  http.post("*/api/fdd/deals", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "deal-new",
        status: "DRAFT",
        created_by: "user-1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        client_name: null,
        client_contact_name: null,
        client_contact_email: null,
        target_company_name: null,
        team_partner_id: null,
        team_manager_id: null,
        scope_qoe: false,
        scope_nwc: false,
        scope_debt: false,
        industry: "general",
        current_phase: "MOU",
        ...body,
      },
      { status: 201 },
    );
  }),

  // ── FDD Industries ──
  http.get("*/api/fdd/industries", () => {
    return HttpResponse.json(mockIndustries);
  }),

  // ── FDD Deal Summary (cross-module) ──
  http.get("*/api/fdd/deals/:dealId/summary", ({ params }) => {
    const deal = mockDeals.find((d) => d.id === params.dealId);
    if (!deal) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json({
      ...mockDealSummary,
      deal_id: deal.id,
      deal_name: deal.name,
      industry: deal.industry,
    });
  }),

  // ── FDD Health ──
  http.get("*/api/fdd/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  // ── KIIS Companies ──
  http.get("*/api/kiis/companies", () => {
    return HttpResponse.json(mockCompanies);
  }),

  http.get("*/api/kiis/companies/:corpCode", ({ params }) => {
    const company = mockCompanies.items.find(
      (c) => c.corp_code === params.corpCode,
    );
    if (!company) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json({
      ...company,
      corp_name_eng: null,
      ceo_nm: null,
      adres: null,
      hm_url: null,
      ir_url: null,
      phn_no: null,
      induty_code: null,
      est_dt: null,
      acc_mt: null,
      jurir_no: null,
      bizr_no: null,
    });
  }),

  // ── KIIS Health & Alerts ──
  http.get("*/api/kiis/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  http.get("*/api/kiis/watchlist", () => {
    return HttpResponse.json(mockWatchlistItems);
  }),

  http.post("*/api/kiis/watchlist", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: 3,
        user_id: 1,
        company_id: body.company_id,
        company_name: "새 회사",
        alert_types: (body.alert_types as string[]) ?? [],
        is_active: true,
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  http.delete("*/api/kiis/watchlist/:companyId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("*/api/kiis/alerts", () => {
    return HttpResponse.json(mockAlerts);
  }),

  http.post("*/api/kiis/alerts/:alertId/read", () => {
    return HttpResponse.json({ success: true });
  }),

  http.get("*/api/kiis/alerts/unread-count", () => {
    return HttpResponse.json({ count: 3 });
  }),

  // ── IM Companies ──
  http.get("*/api/im/companies/:corpCode", ({ params }) => {
    if (params.corpCode === "00126380") {
      return HttpResponse.json(mockImCompany);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  http.post("*/api/im/companies", async ({ request }) => {
    const body = (await request.json()) as { corp_code: string };
    return HttpResponse.json({
      ...mockImCompany,
      corp_code: body.corp_code,
      fetch_status: "PENDING",
    });
  }),

  // ── IM Documents ──
  http.get("*/api/im/documents", () => {
    return HttpResponse.json(mockDocuments);
  }),

  http.get("*/api/im/documents/:documentId", ({ params }) => {
    const doc = mockDocuments.items.find((d) => d.id === params.documentId);
    if (!doc) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(doc);
  }),

  http.post("*/api/im/documents", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "doc-new",
        owner_id: "user-1",
        company_name: "Test Company",
        project_name: null,
        sections: [],
        industry: "general",
        status: "PENDING",
        progress_pct: 0,
        celery_task_id: null,
        pptx_path: null,
        pdf_path: null,
        file_size_bytes: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        completed_at: null,
        ...body,
      },
      { status: 202 },
    );
  }),

  // ── IM Health ──
  http.get("*/api/im/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  // ── IM Download ──
  http.get("*/api/im/documents/:documentId/download", () => {
    return new HttpResponse(new Blob(["mock-pptx"]), {
      headers: { "Content-Type": "application/octet-stream" },
    });
  }),

  // ── KIIS Dashboard/Search/Deals ──
  http.get("*/api/kiis/dashboard/summary", () => {
    return HttpResponse.json(mockDashboardSummary);
  }),

  http.get("*/api/kiis/search", () => {
    return HttpResponse.json(mockKiisSearchResults);
  }),

  http.get("*/api/kiis/deals/by-sector", () => {
    return HttpResponse.json(mockSectorData);
  }),

  http.get("*/api/kiis/deals/trends", () => {
    return HttpResponse.json(mockDealTrends);
  }),

  http.get("*/api/kiis/deals/stats", () => {
    return HttpResponse.json({ total: 89, this_month: 12, avg_amount: "50000000000" });
  }),

  // by-stage: 프론트엔드 훅(useDealsByStage)이 호출하는 실제 경로
  http.get("*/api/kiis/deals/by-stage", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  // by-company: useDealsByCompany 훅
  http.get("*/api/kiis/deals/by-company/:corpCode", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  // by-fund: useDealsByFund 훅
  http.get("*/api/kiis/deals/by-fund/:fundCode", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/kiis/deals", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  // ── KIIS News ──
  http.get("*/api/kiis/news/:articleId", () => {
    return HttpResponse.json({
      id: 1, title: "Sample News", content: "Sample content",
      source: "연합뉴스", published_at: new Date().toISOString(),
      company_name: "삼성전자", corp_code: "00126380",
    });
  }),

  http.get("*/api/kiis/news", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  http.post("*/api/kiis/news/collect", () => {
    return HttpResponse.json({ message: "Collection started", task_id: "mock-task" });
  }),

  // ── KIIS Funds (KOFIA) — 실제 백엔드로 패스스루 ──
  // KOFIA 펀드 API는 실제 ProFrame 데이터를 사용하므로 MSW에서 bypass 처리
  http.get("*/api/kiis/kofia/funds/:fundCode", () => {
    return passthrough();
  }),

  http.get("*/api/kiis/kofia/funds", () => {
    return passthrough();
  }),

  http.get("*/api/kiis/kofia/managers", () => {
    return passthrough();
  }),

  // ── KIIS REITs — 실제 백엔드로 패스스루 ──
  http.get("*/api/kiis/reits/:reitCode", () => {
    return passthrough();
  }),

  http.get("*/api/kiis/reits", () => {
    return passthrough();
  }),

  // ── KIIS Sanctions ──
  http.get("*/api/kiis/sanctions/summary", () => {
    return HttpResponse.json({ total: 0, by_type: {} });
  }),

  // classified: useSanctions 훅이 호출하는 실제 경로
  http.get("*/api/kiis/sanctions/classified/:corpCode/summary", () => {
    return HttpResponse.json({ total: 0, by_type: {}, corp_code: "" });
  }),

  http.get("*/api/kiis/sanctions/classified/:corpCode", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  http.post("*/api/kiis/sanctions/classify/:corpCode", () => {
    return HttpResponse.json({ result: "clean", score: 0 });
  }),

  http.get("*/api/kiis/sanctions", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  // ── KIIS Portfolio ──
  // by-investor: usePortfolio 훅이 호출하는 실제 경로
  http.get("*/api/kiis/portfolio/by-investor/:corpCode/summary", () => {
    return HttpResponse.json({ total_value: 0, fund_count: 0, items: [] });
  }),

  http.get("*/api/kiis/portfolio/by-investor/:corpCode", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  http.get("*/api/kiis/portfolio/:portfolioId", () => {
    return HttpResponse.json({ id: "p-1", name: "Sample Portfolio", items: [] });
  }),

  http.get("*/api/kiis/portfolio", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.post("*/api/kiis/portfolio/by-investor/:corpCode/sync", () => {
    return HttpResponse.json({ message: "Sync started" });
  }),

  http.post("*/api/kiis/portfolio/:portfolioId/check-survival", () => {
    return HttpResponse.json({ results: [] });
  }),

  http.put("*/api/kiis/portfolio/:portfolioId/valuation", () => {
    return HttpResponse.json({ message: "Updated" });
  }),

  // ── KIIS Managers ──
  // movements: useManagerMovements 훅이 호출하는 실제 경로 (복수형)
  http.get("*/api/kiis/managers/movements/by-company/:corpCode", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  http.get("*/api/kiis/managers/movements", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  // profile: useManagerProfile 훅
  http.get("*/api/kiis/managers/:managerName/profile", () => {
    return HttpResponse.json({
      name: "테스트 매니저", company: "테스트 운용사",
      funds_managed: 5, total_aum: "100000000000", career: [],
    });
  }),

  http.get("*/api/kiis/managers/:managerId", () => {
    return HttpResponse.json({
      id: 1, name: "테스트 매니저", company: "테스트 운용사",
      funds_managed: 5, total_aum: "100000000000",
    });
  }),

  http.get("*/api/kiis/managers", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, size: 20 });
  }),

  http.post("*/api/kiis/managers/track", () => {
    return HttpResponse.json({ message: "Tracking started" });
  }),

  // ── KIIS Entities ──
  http.get("*/api/kiis/entities/aliases", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.post("*/api/kiis/entities/resolve", () => {
    return HttpResponse.json({ resolved: [], unresolved: [] });
  }),

  http.post("*/api/kiis/entities/aliases", () => {
    return HttpResponse.json({ id: 1, alias: "new-alias", canonical: "canonical" }, { status: 201 });
  }),

  http.delete("*/api/kiis/entities/aliases/:aliasId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // ── KIIS Disclosures ──
  http.get("*/api/kiis/disclosures/:corpCode", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.post("*/api/kiis/disclosures/:corpCode/sync", () => {
    return HttpResponse.json({ message: "Sync started" });
  }),

  http.post("*/api/kiis/disclosures/kofia/:fundCode/sync", () => {
    return HttpResponse.json({ message: "Sync started" });
  }),

  // ── KIIS Analysis ──
  http.get("*/api/kiis/analysis/reputation/:corpCode", () => {
    return HttpResponse.json({ corp_code: "00126380", score: 85, grade: "A" });
  }),

  http.get("*/api/kiis/analysis/reputation", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.post("*/api/kiis/analysis/reputation/:corpCode/calculate", () => {
    return HttpResponse.json({ score: 85, grade: "A" });
  }),

  // ── KIIS Company Detail ──
  http.get("*/api/kiis/companies/:corpCode/financial", () => {
    return HttpResponse.json({ items: [] });
  }),

  http.get("*/api/kiis/companies/:corpCode/reputation-history", () => {
    return HttpResponse.json({ items: [] });
  }),

  // DART financials: useCompanyFinancials 훅이 호출하는 실제 경로
  http.get("*/api/kiis/dart/companies/:corpCode/financials", () => {
    return HttpResponse.json({ items: [] });
  }),

  // Reputation history: useReputationHistory 훅이 호출하는 실제 경로
  http.get("*/api/kiis/analysis/reputation/:corpCode/history", () => {
    return HttpResponse.json({ items: [] });
  }),

  // ── FDD Deal Sub-resources ──
  http.get("*/api/fdd/deals/:dealId/qoe", () => {
    return HttpResponse.json({ items: [], periods: [] });
  }),

  http.post("*/api/fdd/deals/:dealId/qoe/calculate", () => {
    return HttpResponse.json({ message: "Calculation started" });
  }),

  http.get("*/api/fdd/deals/:dealId/nwc", () => {
    return HttpResponse.json({ items: [], periods: [] });
  }),

  http.post("*/api/fdd/deals/:dealId/nwc/calculate", () => {
    return HttpResponse.json({ message: "Calculation started" });
  }),

  http.get("*/api/fdd/deals/:dealId/debt", () => {
    return HttpResponse.json({ items: [] });
  }),

  http.post("*/api/fdd/deals/:dealId/debt/calculate", () => {
    return HttpResponse.json({ message: "Calculation started" });
  }),

  http.get("*/api/fdd/deals/:dealId/definitions", () => {
    return HttpResponse.json([]);
  }),

  http.post("*/api/fdd/deals/:dealId/definitions", () => {
    return HttpResponse.json({ id: "def-new" }, { status: 201 });
  }),

  http.get("*/api/fdd/deals/:dealId/mappings", () => {
    return HttpResponse.json([]);
  }),

  http.post("*/api/fdd/deals/:dealId/mappings", () => {
    return HttpResponse.json({ id: "map-new" }, { status: 201 });
  }),

  http.get("*/api/fdd/deals/:dealId/issues", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/fdd/deals/:dealId/tie-out", () => {
    return HttpResponse.json({ items: [] });
  }),

  http.get("*/api/fdd/deals/:dealId/uploads", () => {
    return HttpResponse.json([]);
  }),

  http.post("*/api/fdd/deals/:dealId/uploads", () => {
    return HttpResponse.json({ id: "upload-new" }, { status: 201 });
  }),

  http.get("*/api/fdd/deals/:dealId/vdr/folders", () => {
    return HttpResponse.json({ folders: [] });
  }),

  http.post("*/api/fdd/deals/:dealId/vdr/init", () => {
    return HttpResponse.json({ message: "VDR initialized" });
  }),

  http.post("*/api/fdd/deals/:dealId/vdr/folders", () => {
    return HttpResponse.json({ id: "folder-new" }, { status: 201 });
  }),

  http.get("*/api/fdd/deals/:dealId/reports/versions", () => {
    return HttpResponse.json([]);
  }),

  http.post("*/api/fdd/deals/:dealId/reports/versions", () => {
    return HttpResponse.json({ version: 1 }, { status: 201 });
  }),

  http.post("*/api/fdd/deals/:dealId/reports/generate", () => {
    return HttpResponse.json({ message: "Report generation started", task_id: "mock-task" });
  }),

  http.put("*/api/fdd/deals/:dealId", () => {
    return HttpResponse.json({ message: "Updated" });
  }),

  // ── FDD Comments ──
  http.get("*/api/fdd/comments", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.post("*/api/fdd/comments", () => {
    return HttpResponse.json({ id: "comment-new", text: "", created_at: new Date().toISOString() }, { status: 201 });
  }),

  http.patch("*/api/fdd/comments/:commentId", () => {
    return HttpResponse.json({ message: "Updated" });
  }),

  http.delete("*/api/fdd/comments/:commentId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Notifications ──
  http.get("*/api/fdd/notifications", () => {
    return HttpResponse.json(mockNotifications);
  }),

  http.patch("*/api/fdd/notifications/:id/read", () => {
    return HttpResponse.json({ success: true });
  }),

  http.patch("*/api/fdd/notifications/read-all", () => {
    return HttpResponse.json({ success: true });
  }),

  // ── Exports ──
  http.get("*/api/fdd/exports", () => {
    return HttpResponse.json(mockExports);
  }),

  http.delete("*/api/fdd/exports/:exportId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // ── FDD Settings & Integrations ──
  http.get("*/api/fdd/settings/email-preferences", () => {
    return HttpResponse.json({ notifications_enabled: true, digest_frequency: "daily" });
  }),

  http.put("*/api/fdd/settings/email-preferences", () => {
    return HttpResponse.json({ message: "Updated" });
  }),

  http.get("*/api/fdd/webhooks", () => {
    return HttpResponse.json([]);
  }),

  http.post("*/api/fdd/webhooks", () => {
    return HttpResponse.json({ id: "wh-new", url: "", events: [] }, { status: 201 });
  }),

  // ── FDD Users & Profile ──
  http.post("*/api/fdd/auth/users", () => {
    return HttpResponse.json({ id: "user-new", email: "", role: "VIEWER" }, { status: 201 });
  }),

  http.put("*/api/fdd/auth/users/:userId", () => {
    return HttpResponse.json({ message: "Updated" });
  }),

  http.post("*/api/fdd/auth/change-password", () => {
    return HttpResponse.json({ message: "Password changed" });
  }),

  // ── Audit Logs ──
  http.get("*/api/fdd/audit-logs/export", () => {
    const csv =
      "Timestamp,User,Action,Entity Type,Entity ID,Deal ID,IP Address,Changed Fields\n";
    return new HttpResponse(csv, {
      headers: { "Content-Type": "text/csv" },
    });
  }),

  http.get("*/api/fdd/audit-logs", ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get("limit") ?? 20);
    const offset = Number(url.searchParams.get("offset") ?? 0);

    const mockItems = Array.from({ length: 3 }, (_, i) => ({
      id: `audit-${i + 1}`,
      deal_id: null,
      entity_type: "deal",
      entity_id: `entity-${i + 1}`,
      action: ["CREATE", "UPDATE", "DELETE"][i % 3],
      actor: `user${i}@fdd.dev`,
      old_value: null,
      new_value: null,
      user_id: `user-${i + 1}`,
      user_email: `user${i}@fdd.dev`,
      user_role: "ADMIN",
      ip_address: "127.0.0.1",
      before_state: null,
      after_state: null,
      changed_fields: null,
      session_id: null,
      request_id: null,
      expires_at: null,
      created_at: new Date().toISOString(),
    }));

    return HttpResponse.json({
      total: mockItems.length,
      items: mockItems.slice(offset, offset + limit),
      limit,
      offset,
    });
  }),

  // ── MA (Deal Management) ──
  http.get("*/api/ma/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  http.get("*/api/ma/transactions", () => {
    return HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 });
  }),

  http.get("*/api/ma/dashboard/stats", () => {
    return HttpResponse.json({
      total_transactions: 0,
      active_transactions: 0,
      by_phase: {},
      by_status: {},
    });
  }),
];
