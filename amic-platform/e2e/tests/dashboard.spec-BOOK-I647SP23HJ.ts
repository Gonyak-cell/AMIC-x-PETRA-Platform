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

    // Click "New Document" quick action
    await page.getByText("New Document").click();
    await expect(page).toHaveURL(/\/docs\/new/);
  });

  test("module cards navigate to correct pages", async ({ page }) => {
    await page.goto("/");

    // Click Deal Doc Studio module card
    await page.getByText("Deal Doc Studio").click();
    await expect(page).toHaveURL(/\/docs/);
  });
});
