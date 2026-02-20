import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { ImDocumentsPage } from "../pages/im-documents.page";

test.describe("IM Document List — Deep Data Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("document table renders project names from API", async ({ page }) => {
    const docs = new ImDocumentsPage(page);
    await docs.goto();
    await docs.expectLoaded();

    // mockDocuments includes "Samsung IM" and "SK IM"
    await docs.expectDocumentVisible("Samsung IM");
    await docs.expectDocumentVisible("SK IM");
  });

  test("KPI cards show correct document counts", async ({ page }) => {
    const docs = new ImDocumentsPage(page);
    await docs.goto();
    await docs.expectLoaded();

    // mockDocuments: 2 total, 1 GENERATING (in progress), 1 COMPLETED, 0 FAILED
    await docs.expectKpiValue("Total", "2");
    await docs.expectKpiValue("In Progress", "1");
    await docs.expectKpiValue("Completed", "1");
    await docs.expectKpiValue("Failed", "0");
  });

  test("document status badges render correctly", async ({ page }) => {
    const docs = new ImDocumentsPage(page);
    await docs.goto();
    await docs.expectLoaded();

    // DocumentStatusBadge renders status text
    await expect(page.locator("table").getByText("COMPLETED")).toBeVisible();
    await expect(page.locator("table").getByText("GENERATING")).toBeVisible();
  });

  test("empty state renders when no documents exist", async ({ page }) => {
    // Override documents to return empty
    await page.route("**/api/im/documents*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      }),
    );

    const docs = new ImDocumentsPage(page);
    await docs.goto();
    await expect(docs.emptyState).toBeVisible();
  });
});
