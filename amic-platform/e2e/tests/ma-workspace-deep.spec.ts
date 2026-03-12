import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import type { Page, Route } from "@playwright/test";

// ── MA Mock Data ───────────────────────────────────────

const TXN_ID = "txn-e2e-001";

const mockTransaction = {
  id: TXN_ID,
  code_name: "SE26-E2E-01",
  name: "E2E 테스트 프로젝트",
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

const mockPhaseStatus = {
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

const mockPhaseStatusAllMet = {
  ...mockPhaseStatus,
  prerequisites: mockPhaseStatus.prerequisites.map((p) => ({
    ...p,
    satisfied: true,
  })),
  all_met: true,
  can_advance: true,
  blocking_reasons: [],
  pending_acknowledgements: ["dd_items_complete"],
  requires_user_acknowledgement: true,
};

const mockWorkspaceSummary = {
  buyer_count: 5,
  engagement_count: 2,
  timeline_count: 3,
  nda_count: 1,
  bid_count: 0,
  dd_item_count: 0,
  contract_count: 0,
  closing_item_count: 0,
  pmi_count: 0,
  earnout_count: 0,
  marketing_material_count: 4,
  financial_model_count: 1,
  legal_document_count: 0,
};

const mockBuyers = [
  {
    id: "buyer-1",
    transaction_id: TXN_ID,
    company_name: "매수자 A사",
    contact_name: "김매수",
    contact_email: "buyer@a.com",
    tier: "TIER_1",
    status: "ACTIVE",
    notes: null,
    created_at: "2026-01-15T00:00:00Z",
    updated_at: "2026-01-15T00:00:00Z",
  },
  {
    id: "buyer-2",
    transaction_id: TXN_ID,
    company_name: "매수자 B사",
    contact_name: "이매수",
    contact_email: "buyer@b.com",
    tier: "TIER_2",
    status: "ACTIVE",
    notes: null,
    created_at: "2026-01-16T00:00:00Z",
    updated_at: "2026-01-16T00:00:00Z",
  },
];

// ── Helper ─────────────────────────────────────────────

function json(route: Route, data: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(data),
  });
}

/** Mock all MA workspace APIs for a single transaction */
async function mockMaApis(page: Page, overrides?: { phaseStatus?: unknown }) {
  // Core platform APIs (auth, health, notifications)
  await mockAllApis(page);

  // Transaction
  await page.route(`**/api/ma/transactions/${TXN_ID}`, (route) =>
    json(route, mockTransaction),
  );

  // Workflow
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/workflow/phase-status`,
    (route) => json(route, overrides?.phaseStatus ?? mockPhaseStatus),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/workflow/advance`,
    (route) => json(route, { ...mockTransaction, phase: "BIDDING" }),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/workflow/status`,
    (route) => json(route, mockTransaction),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/workflow/auto-advance-notification`,
    (route) => json(route, null),
  );

  // Workspace summary
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/workspace-summary`,
    (route) => json(route, mockWorkspaceSummary),
  );

  // Sub-resources
  await page.route(`**/api/ma/transactions/${TXN_ID}/buyers`, (route) =>
    json(route, { items: mockBuyers, total: mockBuyers.length }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/engagements`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/timeline`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/ndas`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/bids`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/dd-checklist`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/contracts`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/closing-checklist`,
    (route) => json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/pmi-tasks`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/earnout-milestones`,
    (route) => json(route, { items: [], total: 0 }),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/marketing-materials`,
    (route) => json(route, { items: [], total: 0 }),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/financial-models`,
    (route) => json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/meeting-logs`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/attachments*`, (route) =>
    json(route, { items: [], total: 0 }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/members`, (route) =>
    json(route, []),
  );

  // VDR
  await page.route(`**/api/ma/transactions/${TXN_ID}/vdr/folders`, (route) =>
    json(route, []),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/vdr/summary`, (route) =>
    json(route, {
      total_folders: 0,
      total_documents: 0,
      total_size_bytes: 0,
      vdr_initialized: false,
    }),
  );
  await page.route(`**/api/ma/transactions/${TXN_ID}/vdr/documents`, (route) =>
    json(route, []),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/vdr/access-logs`,
    (route) => json(route, []),
  );

  // Short list
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/short-list/overview`,
    (route) => json(route, { tiers: {}, total: 0 }),
  );
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/short-list/marketing-overview`,
    (route) => json(route, []),
  );

  // Legal documents
  await page.route(
    `**/api/ma/transactions/${TXN_ID}/legal-documents`,
    (route) => json(route, []),
  );
}

// ── Tests ──────────────────────────────────────────────

test.describe("MA Workspace — Deep Data Verification", () => {
  test("workspace loads with transaction name and status badge", async ({
    page,
  }) => {
    await mockMaApis(page);
    await page.goto(`/ma/transactions/${TXN_ID}`);

    // Transaction name in hero heading
    await expect(page.locator("h1").first()).toContainText(
      "E2E 테스트 프로젝트",
    );

    // Status badge shows ACTIVE
    await expect(page.getByText("ACTIVE").first()).toBeVisible();

    // Current phase label ("현재: 마케팅" in status area)
    await expect(page.getByText("현재:", { exact: false }).first()).toBeVisible();
  });

  test("PhaseActionPanel renders prerequisites with correct icons", async ({
    page,
  }) => {
    await mockMaApis(page);
    await page.goto(`/ma/transactions/${TXN_ID}`);

    // Wait for phase panel to load
    await expect(page.getByText("현재 단계:", { exact: false })).toBeVisible();

    // 3 prerequisites from mock data
    await expect(page.getByText("Short List 매수자 1명 이상")).toBeVisible();
    await expect(
      page.getByText("NDA 체결 또는 자료 배포 1건 이상"),
    ).toBeVisible();
    await expect(page.getByText("DD 항목 없음 — 확인 필요")).toBeVisible();

    // Progress bar shows 2/3 (satisfied=true count)
    await expect(page.getByText("2/3")).toBeVisible();
    await expect(page.getByText("67%")).toBeVisible();

    // Gate summary is displayed
    await expect(
      page.getByText("입찰 진입: Short List 매수자 및 NDA/자료 배포 완료 필요"),
    ).toBeVisible();

    // Acknowledgement checkbox exists (requires_acknowledgement=true item)
    await expect(page.locator("input[type='checkbox']")).toBeVisible();

    // Acknowledgement warning is displayed
    await expect(
      page.getByText("단계 전환을 위해 확인이 필요한 항목이 있습니다"),
    ).toBeVisible();
  });

  test("tabs reflect MARKETING phase visibility", async ({ page }) => {
    await mockMaApis(page);
    await page.goto(`/ma/transactions/${TXN_ID}`);

    // Wait for tabs to render
    await expect(page.getByRole("tab").first()).toBeVisible();

    const tabLabels = await page.getByRole("tab").allTextContents();
    const normalised = tabLabels.map((t) => t.replace(/\d+/g, "").trim());

    // MARKETING phase shows: overview, buyers, marketing-logs, vdr, risks, compliance, notes-approvals
    // The tab labels depend on the Korean labels used in useWorkspaceTabs
    expect(normalised.length).toBeGreaterThanOrEqual(4);

    // Buyers tab should be visible in MARKETING phase
    const hasBuyers = tabLabels.some((t) => /매수자|Buyers|buyers/i.test(t));
    expect(hasBuyers).toBeTruthy();
  });

  test("Buyers tab displays buyer cards from mock data", async ({ page }) => {
    await mockMaApis(page);
    // Navigate directly to buyers tab
    await page.goto(`/ma/transactions/${TXN_ID}/buyers`);

    // Wait for the page to load
    await expect(page.locator("h1").first()).toContainText(
      "E2E 테스트 프로젝트",
    );

    // Mock buyers should be rendered
    await expect(page.getByText("매수자 A사")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("매수자 B사")).toBeVisible();
  });

  test("advance button is disabled when can_advance is false", async ({
    page,
  }) => {
    await mockMaApis(page);
    await page.goto(`/ma/transactions/${TXN_ID}`);

    // Wait for hero to load
    await expect(page.locator("h1").first()).toContainText(
      "E2E 테스트 프로젝트",
    );

    // When can_advance=false, blocking_reasons are shown instead of advance button
    await expect(
      page.getByText("NDA 체결 또는 자료 배포가 필요합니다"),
    ).toBeVisible();

    // Advance button should NOT be visible when can_advance is false
    await expect(
      page.getByRole("button", { name: /입찰 단계로/ }),
    ).not.toBeVisible();
  });

  test("advance button appears and is disabled until ack checked when can_advance is true", async ({
    page,
  }) => {
    // Override with all-met phase status
    await mockMaApis(page, { phaseStatus: mockPhaseStatusAllMet });
    await page.goto(`/ma/transactions/${TXN_ID}`);

    // Wait for hero to load
    await expect(page.locator("h1").first()).toContainText(
      "E2E 테스트 프로젝트",
    );

    // Advance button should be visible (can_advance=true, next_phase=BIDDING)
    const advanceBtn = page.getByRole("button", { name: /입찰 단계로/ });
    await expect(advanceBtn).toBeVisible({ timeout: 10_000 });

    // Button should be disabled because pending_acknowledgements exist and checkbox is unchecked
    await expect(advanceBtn).toBeDisabled();

    // Check the acknowledgement checkbox (use label text for precision)
    const checkbox = page
      .locator("label")
      .filter({ hasText: "DD 항목 없음" })
      .locator("input[type='checkbox']");
    await checkbox.check();

    // After checking, advance button should be enabled
    // (React state propagates: PhaseActionPanel acks -> useEffect -> parent -> HeroActions)
    await expect(advanceBtn).toBeEnabled({ timeout: 10_000 });
  });
});
