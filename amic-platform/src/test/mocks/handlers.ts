import { http, HttpResponse } from "msw";
import {
  mockDeals,
  mockCompanies,
  mockDocuments,
  mockUser,
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
} from "./data";

export const handlers = [
  // ── Auth ──
  http.post("*/api/fdd/auth/login", () => {
    return HttpResponse.json({
      access_token: "mock-access-token",
      refresh_token: "mock-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    });
  }),

  http.get("*/api/fdd/auth/me", ({ request }) => {
    const authHeader = request.headers.get("Authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      return new HttpResponse(null, { status: 401 });
    }
    return HttpResponse.json(mockUser);
  }),

  http.get("*/api/fdd/auth/users", () => {
    return HttpResponse.json([]);
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

  // ── Notifications ──
  http.get("*/api/fdd/notifications", () => {
    return HttpResponse.json(mockNotifications);
  }),

  // ── Exports ──
  http.get("*/api/fdd/exports", () => {
    return HttpResponse.json(mockExports);
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
];
