import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";

test.describe("Dashboard — Deep Data Verification", () => {
  test("KPI cards display correct numeric values from API data", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/");

    // mockDeals has 1 ACTIVE, 1 DRAFT deal; alerts count = 3; 1 GENERATING doc
    await expect(page.getByText("Active FDD Deals")).toBeVisible();

    // Find KPI card values — each KpiCard renders label + value
    // ACTIVE deals = 1
    const activeFddCard = page.getByText("Active FDD Deals").locator("../..");
    await expect(activeFddCard).toContainText("1");

    // Watchlist Alerts = 3
    const alertsCard = page.getByText("Watchlist Alerts").locator("../..");
    await expect(alertsCard).toContainText("3");

    // IM In Progress = 1 (GENERATING status)
    const imCard = page.getByText("IM In Progress").locator("../..");
    await expect(imCard).toContainText("1");

    // Draft Deals = 1
    const draftCard = page.getByText("Draft Deals").locator("../..");
    await expect(draftCard).toContainText("1");
  });

  test("KPI cards show 0 with empty data", async ({ page }) => {
    // Mock empty responses
    await page.route("**/api/fdd/auth/me", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "user-1", email: "admin@amic.co.kr", display_name: "Admin User", role: "ADMIN", is_active: true, created_at: "2025-01-01T00:00:00Z" }) }),
    );
    await page.route("**/api/fdd/deals*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );
    await page.route("**/api/kiis/alerts/unread-count", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ count: 0 }) }),
    );
    await page.route("**/api/im/documents*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) }),
    );
    await page.route("**/api/fdd/health", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) }),
    );
    await page.route("**/api/kiis/health", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) }),
    );
    await page.route("**/api/im/health", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) }),
    );
    await page.route("**/api/fdd/notifications", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );

    await page.goto("/");
    await expect(page.getByText("Active FDD Deals")).toBeVisible();

    const activeFddCard = page.getByText("Active FDD Deals").locator("../..");
    await expect(activeFddCard).toContainText("0");

    const alertsCard = page.getByText("Watchlist Alerts").locator("../..");
    await expect(alertsCard).toContainText("0");
  });

  test("module status shows Connected when all backends respond", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/");

    // All three health endpoints return 200 → "Connected" x 3
    const connectedTexts = page.getByText("Connected");
    await expect(connectedTexts.first()).toBeVisible();
    await expect(connectedTexts).toHaveCount(3);
  });

  test("module status shows Unreachable when a backend fails", async ({ page }) => {
    await mockAllApis(page);
    // Override FDD health to return 500
    await page.route("**/api/fdd/health", (route) =>
      route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) }),
    );
    await page.goto("/");

    await expect(page.getByText("Unreachable").first()).toBeVisible();
  });

  test("KPI shows em-dash when module API errors", async ({ page }) => {
    await mockAllApis(page);
    // Override FDD deals to return 500
    await page.route("**/api/fdd/deals*", (route) =>
      route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "error" }) }),
    );
    await page.goto("/");

    // DashboardPage shows "—" (em dash) when errors.fdd is true
    const activeFddCard = page.getByText("Active FDD Deals").locator("../..");
    await expect(activeFddCard).toContainText("—");
  });

  test("quick action New Deal navigates to deal creation", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/");
    await expect(page.getByText("Active FDD Deals")).toBeVisible();

    // Click "New Deal" quick action
    await page.getByText("New Deal").first().click();
    await expect(page).toHaveURL(/\/fdd\/deals\/new/);
  });
});
