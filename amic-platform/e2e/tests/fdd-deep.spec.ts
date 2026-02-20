import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";

test.describe("FDD Deal List — Deep Data Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("deal table renders deal names from API", async ({ page }) => {
    await page.goto("/fdd/deals");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Deals");

    // mockDeals includes "Project Alpha" and "Project Beta"
    await expect(page.getByText("Project Alpha")).toBeVisible();
    await expect(page.getByText("Project Beta")).toBeVisible();
  });

  test("KPI cards show correct deal counts", async ({ page }) => {
    await page.goto("/fdd/deals");

    // mockDeals: 2 total, 1 ACTIVE, 1 DRAFT, 0 ARCHIVED
    const totalCard = page.getByText("Total Deals").locator("../..");
    await expect(totalCard).toContainText("2");

    const activeCard = page.getByText("Active").first().locator("../..");
    await expect(activeCard).toContainText("1");

    const draftCard = page.getByText("Draft").first().locator("../..");
    await expect(draftCard).toContainText("1");

    const archivedCard = page.getByText("Archived").locator("../..");
    await expect(archivedCard).toContainText("0");
  });

  test("table shows expected column headers", async ({ page }) => {
    await page.goto("/fdd/deals");
    await expect(page.locator("table")).toBeVisible();

    for (const header of ["Deal Name", "Type", "Industry", "Currency", "Reference Date", "Status"]) {
      await expect(page.locator("th", { hasText: header })).toBeVisible();
    }
  });

  test("deal status badges render correctly", async ({ page }) => {
    await page.goto("/fdd/deals");
    await expect(page.locator("table")).toBeVisible();

    // Status badges in table rows
    await expect(page.locator("table").getByText("ACTIVE")).toBeVisible();
    await expect(page.locator("table").getByText("DRAFT")).toBeVisible();
  });

  test("empty state renders when no deals exist", async ({ page }) => {
    // Override deals to return empty array
    await page.route("**/api/fdd/deals*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );

    await page.goto("/fdd/deals");
    await expect(page.getByText("No deals yet")).toBeVisible();
    await expect(page.getByRole("button", { name: /Create Deal/i })).toBeVisible();
  });
});
