import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { AnalyticsPage } from "../pages/analytics.page";

test.describe("Analytics — Deep Data & Chart Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("all three module KPI sections are rendered", async ({ page }) => {
    const analytics = new AnalyticsPage(page);
    await analytics.goto();
    await analytics.expectLoaded();
    await analytics.expectAllSectionsVisible();
  });

  test("FDD KPI cards show correct values", async ({ page }) => {
    const analytics = new AnalyticsPage(page);
    await analytics.goto();
    await analytics.expectLoaded();

    // Default timeRange is "30d" — mock dates are older, so switch to "All Time"
    await page.getByLabel("Time Range").selectOption("all");

    // mockDeals has 2 deals (1 ACTIVE, 1 DRAFT)
    // ModuleKpiSection renders: Total Deals, Active Deals, Avg Cycle, Draft Deals
    const fddSection = page.getByRole("heading", { name: "FDD", level: 3 }).locator("..");
    await expect(fddSection.getByText("Total Deals").locator("../..")).toContainText("2");
    await expect(fddSection.getByText("Active Deals").locator("../..")).toContainText("1");
    await expect(fddSection.getByText("Draft Deals").locator("../..")).toContainText("1");
  });

  test("KIIS KPI cards show correct values from dashboard summary", async ({ page }) => {
    const analytics = new AnalyticsPage(page);
    await analytics.goto();
    await analytics.expectLoaded();

    // mockDashboardSummary: total_companies=150, total_funds=45, total_reits=12
    const kiisSection = page.getByRole("heading", { name: "KIIS", level: 3 }).locator("..");
    await expect(kiisSection.getByText("Companies").locator("../..")).toContainText("150");
    await expect(kiisSection.getByText("Funds").locator("../..")).toContainText("45");
    await expect(kiisSection.getByText("REITs").locator("../..")).toContainText("12");
  });

  test("charts render as SVG elements with drawn content", async ({ page }) => {
    const analytics = new AnalyticsPage(page);
    await analytics.goto();
    await analytics.expectLoaded();

    // Wait for charts to render — Recharts creates SVG inside .recharts-responsive-container
    await analytics.expectChartsRendered();
  });

  test("error banner shows when FDD backend fails", async ({ page }) => {
    await mockAllApis(page);
    // Override FDD deals to return 500
    await page.route("**/api/fdd/deals*", (route) =>
      route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) }),
    );

    const analytics = new AnalyticsPage(page);
    await analytics.goto();
    await analytics.expectLoaded();
    await analytics.expectErrorBanner("fdd");
  });
});
