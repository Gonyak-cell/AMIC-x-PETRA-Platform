import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";

test.describe("Browser Health — JS Error & Hydration Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("dashboard loads without JS errors", async ({ page, consoleMonitor }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Welcome");
    await expect(page.getByText("Active FDD Deals")).toBeVisible();
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("FDD deal list loads without JS errors", async ({ page, consoleMonitor }) => {
    await page.goto("/fdd/deals");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Deals");
    // Wait for table or empty state
    await expect(page.locator("table").or(page.getByText("No deals yet"))).toBeVisible();
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("KIIS company list loads without JS errors", async ({ page, consoleMonitor }) => {
    await page.goto("/kiis/companies");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Companies");
    await expect(page.locator("table").or(page.getByText("No companies found"))).toBeVisible();
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("IM document list loads without JS errors", async ({ page, consoleMonitor }) => {
    await page.goto("/im");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("IM Projects");
    await expect(page.locator("table").or(page.getByText("No IM projects yet"))).toBeVisible();
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("analytics page loads without JS errors", async ({ page, consoleMonitor }) => {
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Cross-Module Analytics");
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("admin pages load without JS errors", async ({ page, consoleMonitor }) => {
    const routes = ["/admin/users", "/admin/activity", "/settings/profile"];
    for (const route of routes) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }
    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("search palette opens without JS errors", async ({ page, consoleMonitor }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Open search palette
    await page.keyboard.press("Control+k");
    await expect(page.locator("[role='dialog'][aria-label='Global search']")).toBeVisible();

    // Type a query
    await page.locator("[aria-label='Search input']").fill("test");
    await page.waitForTimeout(500);

    // Close
    await page.keyboard.press("Escape");
    await expect(page.locator("[role='dialog'][aria-label='Global search']")).toBeHidden();

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("full module navigation flow without JS errors", async ({ page, consoleMonitor }) => {
    // Dashboard
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // FDD
    await page.goto("/fdd/deals");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Deals");

    // KIIS
    await page.goto("/kiis/companies");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Companies");

    // IM
    await page.goto("/im");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("IM Projects");

    // Analytics
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Cross-Module Analytics");

    // Back to Dashboard
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Welcome");

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });
});
