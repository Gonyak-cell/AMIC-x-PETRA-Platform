import { http, HttpResponse } from "msw";
import type { Transaction } from "@/modules/ma/types/transaction";
import type { PhaseCompletionStatus } from "@/modules/ma/types/workflow";

// ── Mock Data ────────────────────────────────────────────

export const mockTransaction: Transaction = {
  id: "txn-1",
  code_name: "SE26-TST-01",
  name: "테스트 프로젝트",
  deal_type: "SE",
  side: "SELL",
  phase: "MARKETING",
  status: "ACTIVE",
  target_company_name: "대상기업",
  target_corp_code: null,
  client_name: "클라이언트",
  estimated_deal_value: "50000000000",
  currency: "KRW",
  deal_structure: null,
  investment_type: null,
  industry: "general",
  lead_advisor_email: "jwsuh@amic.kr",
  deal_captain_email: null,
  target_close_date: null,
  sale_process: null,
  control_transfer: null,
  target_stake: null,
  new_share_ratio: null,
  old_share_ratio: null,
  valuation_basis: null,
  cross_border: null,
  target_buyer_types: null,
  exclusivity: null,
  exclusivity_deadline: null,
  fdd_deal_id: null,
  im_document_id: null,
  notes: null,
  corporate_info: null,
  financial_summary: null,
  is_deleted: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const mockPhaseStatus: PhaseCompletionStatus = {
  current_phase: "MARKETING",
  prerequisites: [
    {
      field: "short_list_buyers",
      label: "Short List 매수자 1명 이상",
      satisfied: true,
      current_value: "2명",
      target_value: "1명 이상",
    },
    {
      field: "nda_or_distribution",
      label: "NDA 체결 또는 자료 배포 1건 이상",
      satisfied: false,
      current_value: "0건",
      target_value: "1건 이상",
    },
    {
      field: "dd_items_complete",
      label: "DD 항목 없음 — 확인 필요",
      satisfied: true,
      current_value: "0건",
      requires_acknowledgement: true,
    },
  ],
  all_met: false,
  can_advance: false,
  blocking_reasons: ["NDA 체결 또는 자료 배포가 필요합니다"],
  next_phase: "BIDDING",
  previous_phase: "PREPARATION",
  gate_summary: "입찰 진입: Short List 매수자 및 NDA/자료 배포 완료 필요",
  pending_acknowledgements: ["dd_items_complete"],
  requires_user_acknowledgement: true,
};

// ── Handlers ─────────────────────────────────────────────

export const maHandlers = [
  // Health
  http.get("*/api/ma/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),
  http.get("*/api/ma/transactions", () => {
    return HttpResponse.json({ items: [mockTransaction], total: 1 });
  }),

  // Transaction CRUD
  http.get("*/api/ma/transactions/:txnId", ({ params }) => {
    if (params.txnId === mockTransaction.id) {
      return HttpResponse.json(mockTransaction);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  http.post("*/api/ma/transactions", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      { ...mockTransaction, ...body, id: "txn-new" },
      { status: 201 },
    );
  }),

  http.patch("*/api/ma/transactions/:txnId", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...mockTransaction, ...body });
  }),

  http.delete("*/api/ma/transactions/:txnId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Workflow
  http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () => {
    return HttpResponse.json(mockPhaseStatus);
  }),

  http.post(
    "*/api/ma/transactions/:txnId/workflow/advance",
    async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        ...mockTransaction,
        phase: body.to_phase ?? "BIDDING",
      });
    },
  ),

  http.post(
    "*/api/ma/transactions/:txnId/workflow/status",
    async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        ...mockTransaction,
        status: body.to_status ?? "ACTIVE",
      });
    },
  ),

  // Workspace summary (badge counts)
  http.get("*/api/ma/transactions/:txnId/workspace-summary", () => {
    return HttpResponse.json({
      buyer_count: 0,
      engagement_count: 0,
      timeline_count: 0,
      nda_count: 0,
      bid_count: 0,
      dd_item_count: 0,
      contract_count: 0,
      closing_item_count: 0,
      pmi_count: 0,
      earnout_count: 0,
      marketing_material_count: 0,
      financial_model_count: 0,
      legal_document_count: 0,
    });
  }),

  // Sub-resources (empty defaults for badge counts)
  http.get("*/api/ma/transactions/:txnId/buyers", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/engagements", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/timeline", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/ndas", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/bids", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/dd-checklist", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/contracts", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/closing-checklist", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/pmi-tasks", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/earnout-milestones", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/marketing-materials", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/financial-models", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/meeting-logs", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/attachments", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  http.get("*/api/ma/transactions/:txnId/members", () => {
    return HttpResponse.json([]);
  }),

  // VDR
  http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
    return HttpResponse.json([]);
  }),

  http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
    return HttpResponse.json({
      total_folders: 0,
      total_documents: 0,
      total_size_bytes: 0,
      vdr_initialized: false,
    });
  }),

  // VDR all documents
  http.get("*/api/ma/transactions/:txnId/vdr/documents", () => {
    return HttpResponse.json([]);
  }),

  // VDR init (auto-init for uninitialized VDR)
  http.post("*/api/ma/transactions/:txnId/vdr/init", () => {
    return HttpResponse.json({ initialized: true });
  }),

  // VDR access logs
  http.get("*/api/ma/transactions/:txnId/vdr/access-logs", () => {
    return HttpResponse.json([]);
  }),

  // Document extractions
  http.get("*/api/ma/transactions/:txnId/extractions", () => {
    return HttpResponse.json({ items: [], total: 0 });
  }),

  // Auto-advance notification
  http.get(
    "*/api/ma/transactions/:txnId/workflow/auto-advance-notification",
    () => {
      return HttpResponse.json(null);
    },
  ),

  // Short list overview
  http.get("*/api/ma/transactions/:txnId/short-list/overview", () => {
    return HttpResponse.json({ tiers: {}, total: 0 });
  }),

  // Short-list marketing overview — useShortListOverview expects BuyerStageSummary[] directly
  http.get("*/api/ma/transactions/:txnId/short-list/marketing-overview", () => {
    return HttpResponse.json([]);
  }),

  // Legal documents — useLegalDocuments expects LegalDocument[] directly
  http.get("*/api/ma/transactions/:txnId/legal-documents", () => {
    return HttpResponse.json([]);
  }),
];
