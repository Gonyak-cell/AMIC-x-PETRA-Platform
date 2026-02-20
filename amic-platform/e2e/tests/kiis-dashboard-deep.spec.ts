import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { KiisDashboardPage } from "../pages/kiis-dashboard.page";

test.describe("KIIS Dashboard — Deep Data Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("dashboard heading and KPI cards render", async ({ page }) => {
    const dashboard = new KiisDashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    await dashboard.expectKpiVisible("Companies");
    await dashboard.expectKpiVisible("Funds");
    await dashboard.expectKpiVisible("News (Recent)");
    await dashboard.expectKpiVisible("Total Deals");
  });

  test("KPI cards display correct values from API", async ({ page }) => {
    const dashboard = new KiisDashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    // mockDashboardSummary: 기업=150, 펀드=45, 딜=89, recent_news_count=15
    await dashboard.expectKpiValue("Companies", "150");
    await dashboard.expectKpiValue("Funds", "45");
    await dashboard.expectKpiValue("Total Deals", "89");
    await dashboard.expectKpiValue("News (Recent)", "15");
  });

  test("Recent Deals section renders", async ({ page }) => {
    const dashboard = new KiisDashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    await expect(page.getByText("Recent Deals").first()).toBeVisible();
    // mockDashboardSummary has 1 recent deal with target_company "Target Inc"
    await expect(page.getByText("Target Inc").first()).toBeVisible();
  });

  test("Risk Companies section renders", async ({ page }) => {
    const dashboard = new KiisDashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    await expect(page.getByText("Risk Companies").first()).toBeVisible();
    // mockDashboardSummary has 1 risk company: 삼성전자
    await expect(page.getByText("삼성전자").first()).toBeVisible();
  });

  test("empty state renders when no recent deals", async ({ page }) => {
    await page.route("**/api/kiis/dashboard/summary", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          counts: [
            { label: "기업", count: 0 },
            { label: "펀드", count: 0 },
            { label: "딜", count: 0 },
          ],
          recent_news_count: 0,
          recent_deals: [],
          risk_companies: [],
          data_freshness: [],
        }),
      }),
    );

    const dashboard = new KiisDashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    await expect(page.getByText("No recent deals").first()).toBeVisible();
    await expect(page.getByText("No risk companies").first()).toBeVisible();
  });
});
