/**
 * E2E: 딜 생성/목록/탐색 테스트.
 */

import { test, expect } from "../fixtures/auth.fixture";
import { DealListPage } from "../pages/deal-list.page";
import { DealWorkspacePage } from "../pages/deal-workspace.page";
import { uniqueDealName } from "../utils/test-data";

test.describe("Deal Management", () => {
  test("should display deals list page", async ({ authedPage }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    await expect(dealList.heading).toBeVisible();
    await expect(dealList.newDealButton).toBeVisible();
  });

  test("should create a new deal via form", async ({ authedPage }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    const name = uniqueDealName("Deal Create");
    await dealList.createDeal({
      name,
      type: "COMPLETION_ACCOUNTS",
      referenceDate: "2025-12-31",
      periodStart: "2025-01-01",
      periodEnd: "2025-12-31",
    });

    // Verify the deal appears in the list
    await expect(authedPage.getByText(name)).toBeVisible({ timeout: 10_000 });
  });

  test("should create a Locked Box deal", async ({ authedPage }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    const name = uniqueDealName("LB");
    await dealList.createDeal({
      name,
      type: "LOCKED_BOX",
      currency: "USD",
      referenceDate: "2025-06-30",
      periodStart: "2025-01-01",
      periodEnd: "2025-06-30",
    });

    await expect(authedPage.getByText(name)).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText("Locked Box")).toBeVisible();
  });

  test("should navigate to deal workspace on click", async ({
    authedPage,
  }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    // Create a deal first
    const name = uniqueDealName("Nav");
    await dealList.createDeal({ name });

    // Click the deal
    await dealList.clickDeal(name);

    // Verify we're on the workspace page with tabs
    const workspace = new DealWorkspacePage(authedPage);
    await expect(workspace.uploadsTab).toBeVisible();
    await expect(workspace.mappingTab).toBeVisible();
    await expect(workspace.qoeTab).toBeVisible();
    await expect(workspace.reportTab).toBeVisible();
  });

  test("should navigate between workspace tabs", async ({ authedPage }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    const name = uniqueDealName("Tabs");
    await dealList.createDeal({ name });
    await dealList.clickDeal(name);

    const workspace = new DealWorkspacePage(authedPage);

    // Navigate through tabs
    await workspace.navigateToTab("Uploads");
    await expect(authedPage).toHaveURL(/\/uploads/);

    await workspace.navigateToTab("Mapping");
    await expect(authedPage).toHaveURL(/\/mapping/);

    await workspace.navigateToTab("QoE");
    await expect(authedPage).toHaveURL(/\/qoe/);

    await workspace.navigateToTab("NWC");
    await expect(authedPage).toHaveURL(/\/nwc/);

    await workspace.navigateToTab("Net Debt");
    await expect(authedPage).toHaveURL(/\/netdebt/);

    await workspace.navigateToTab("Report");
    await expect(authedPage).toHaveURL(/\/report/);
  });

  test("should cancel deal creation form", async ({ authedPage }) => {
    const dealList = new DealListPage(authedPage);
    await dealList.goto();

    await dealList.newDealButton.click();
    await expect(dealList.dealNameInput).toBeVisible();

    await dealList.cancelButton.click();
    await expect(dealList.dealNameInput).not.toBeVisible();
  });
});
