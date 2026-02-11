import { http, HttpResponse } from "msw";
import { mockDeals, mockCompanies, mockDocuments, mockUser } from "./data";

export const handlers = [
  // ── Auth ──
  http.post("/api/fdd/auth/login", () => {
    return HttpResponse.json({
      access_token: "mock-access-token",
      refresh_token: "mock-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    });
  }),

  http.get("/api/fdd/auth/me", () => {
    return HttpResponse.json(mockUser);
  }),

  http.get("/api/fdd/auth/users", () => {
    return HttpResponse.json([]);
  }),

  // ── FDD Deals ──
  http.get("/api/fdd/deals", () => {
    return HttpResponse.json(mockDeals);
  }),

  http.get("/api/fdd/deals/:dealId", ({ params }) => {
    const deal = mockDeals.find((d) => d.id === params.dealId);
    if (!deal) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(deal);
  }),

  http.post("/api/fdd/deals", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "deal-new",
        ...body,
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
        current_phase: "MOU",
      },
      { status: 201 },
    );
  }),

  // ── FDD Health ──
  http.get("/api/fdd/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  // ── KIIS Companies ──
  http.get("/api/kiis/companies", () => {
    return HttpResponse.json(mockCompanies);
  }),

  http.get("/api/kiis/companies/:corpCode", ({ params }) => {
    const company = mockCompanies.items.find(
      (c) => c.corp_code === params.corpCode,
    );
    if (!company) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json({
      ...company,
      industry: null,
      est_dt: null,
      homepage: null,
      ir_url: null,
      phn_no: null,
      fax_no: null,
      jurir_no: null,
      bizr_no: null,
    });
  }),

  // ── KIIS Health & Alerts ──
  http.get("/api/kiis/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  http.get("/api/kiis/alerts/unread-count", () => {
    return HttpResponse.json({ count: 3 });
  }),

  // ── IM Documents ──
  http.get("/api/im/documents", () => {
    return HttpResponse.json(mockDocuments);
  }),

  http.get("/api/im/documents/:documentId", ({ params }) => {
    const doc = mockDocuments.items.find((d) => d.id === params.documentId);
    if (!doc) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(doc);
  }),

  http.post("/api/im/documents", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "doc-new",
        owner_id: "user-1",
        company_name: "Test Company",
        project_name: null,
        sections: [],
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
      { status: 201 },
    );
  }),

  // ── IM Health ──
  http.get("/api/im/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),
];
