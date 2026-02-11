import { test, expect } from "@playwright/test";
import { DashboardPage } from "../pages/dashboard.page";

test.describe("Dashboard", () => {
  test("loads with KPI cards", async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await dashboard.expectLoaded();

    // KPI cards should be visible
    await expect(
      page.getByText(/Active FDD Deals|Watchlist Alerts|IM In Progress|Draft Deals/).first(),
    ).toBeVisible();
  });

  test("module status indicators are visible", async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await expect(page.getByText("Module Status")).toBeVisible();
  });

  test("quick action cards navigate correctly", async ({ page }) => {
    await page.goto("/");

    // Click "New Deal" quick action
    await page.getByText("New Deal").click();
    await expect(page).toHaveURL(/\/fdd\/deals\/new/);
  });

  test("module cards navigate to correct pages", async ({ page }) => {
    await page.goto("/");

    // Click Auto FDD module card
    await page.getByText("Auto FDD").click();
    await expect(page).toHaveURL(/\/fdd/);
  });
});
