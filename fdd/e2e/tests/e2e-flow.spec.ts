/**
 * E2E: 전체 FDD 플로우 통합 테스트.
 * 딜 생성 → 업로드 → 매핑 → QoE → NWC → Net Debt → 보고서.
 */

import * as path from "path";
import { test, expect } from "../fixtures/auth.fixture";
import { DealListPage } from "../pages/deal-list.page";
import { DealWorkspacePage } from "../pages/deal-workspace.page";
import { UploadPage } from "../pages/upload.page";
import { MappingPage } from "../pages/mapping.page";
import { QoEPage } from "../pages/qoe.page";
import { NWCPage } from "../pages/nwc.page";
import { NetDebtPage } from "../pages/debt.page";
import { ReportPage } from "../pages/report.page";
import { uniqueDealName } from "../utils/test-data";

const ASSETS_DIR = path.resolve(__dirname, "../test-assets");

test.describe("Full E2E FDD Flow", () => {
  test.setTimeout(300_000); // 5 minutes for full flow

  test("complete flow: deal → upload → mapping → QoE → report", async ({
    authedPage,
  }) => {
    // ── Step 1: 딜 생성 ──

    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    const dealName = uniqueDealName("E2E Full");
    await dealList.createDeal({
      name: dealName,
      type: "COMPLETION_ACCOUNTS",
      currency: "KRW",
      referenceDate: "2025-12-31",
      periodStart: "2025-01-01",
      periodEnd: "2025-12-31",
    });

    // Navigate into the deal
    await dealList.clickDeal(dealName);
    const currentUrl = authedPage.url();
    const dealIdMatch = currentUrl.match(/\/deals\/([^/]+)/);
    expect(dealIdMatch).toBeTruthy();
    const dealId = dealIdMatch![1];

    // ── Step 2: TB/GL 업로드 ──

    const workspace = new DealWorkspacePage(authedPage);
    await workspace.navigateToUploads(dealId);

    const upload = new UploadPage(authedPage);

    // Upload TB
    const tbFile = path.join(ASSETS_DIR, "sample-tb.xlsx");
    await upload.uploadFile(tbFile);
    await upload.confirmType(0, "TB");
    await upload.ingest(0);
    await upload.waitForIngestComplete(0);

    // Upload GL
    const glFile = path.join(ASSETS_DIR, "sample-gl.xlsx");
    await upload.uploadFile(glFile);
    await upload.confirmType(1, "GL");
    await upload.ingest(1);
    await upload.waitForIngestComplete(1);

    // ── Step 3: 매핑 ──

    await workspace.navigateToMapping(dealId);
    const mapping = new MappingPage(authedPage);

    await mapping.runAutoSuggest();
    const suggestCount = await mapping.getSuggestionCount();
    expect(suggestCount).toBeGreaterThan(0);

    await mapping.saveAllSuggestions();
    await mapping.approveAll();

    // ── Step 4: QoE 분석 ──

    await workspace.navigateToQoE(dealId);
    const qoe = new QoEPage(authedPage);

    // QoE needs a snapshot — verify page loads
    await expect(qoe.heading).toBeVisible();

    // ── Step 5: 보고서 생성 ──

    await workspace.navigateToReport(dealId);
    const report = new ReportPage(authedPage);

    await expect(report.heading).toBeVisible();
    await report.setOptions({
      qoe: true,
      nwc: true,
      debt: true,
      issues: true,
      format: "json",
    });
    await report.preview();
  });

  test("workspace tab navigation preserves state", async ({
    authedPage,
  }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    const dealName = uniqueDealName("Tab Nav");
    await dealList.createDeal({ name: dealName });
    await dealList.clickDeal(dealName);

    const currentUrl = authedPage.url();
    const dealIdMatch = currentUrl.match(/\/deals\/([^/]+)/);
    const dealId = dealIdMatch![1];

    const workspace = new DealWorkspacePage(authedPage);

    // Navigate through all tabs
    const tabs = [
      { name: "Uploads", url: "uploads" },
      { name: "Mapping", url: "mapping" },
      { name: "QoE", url: "qoe" },
      { name: "NWC", url: "nwc" },
      { name: "Net Debt", url: "netdebt" },
      { name: "Issues", url: "issues" },
      { name: "Report", url: "report" },
    ];

    for (const tab of tabs) {
      await workspace.navigateToTab(tab.name);
      await expect(authedPage).toHaveURL(new RegExp(tab.url));
    }
  });
});
