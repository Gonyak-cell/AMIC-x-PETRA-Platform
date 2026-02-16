import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { SearchPalettePage } from "../pages/search-palette.page";

test.describe("Global Search — Deep Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/");
    // Wait for dashboard to load before opening search
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("search palette opens and input is focused", async ({ page }) => {
    const search = new SearchPalettePage(page);
    await search.open();
    await expect(search.searchInput).toBeFocused();
  });

  test("typing a query shows search results", async ({ page }) => {
    const search = new SearchPalettePage(page);
    await search.open();
    await search.search("test");

    // Results should appear (mocked APIs return data for any search)
    const count = await search.resultItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test("search results display module badges", async ({ page }) => {
    const search = new SearchPalettePage(page);
    await search.open();
    await search.search("test");

    // Module badges should be visible in the results area
    const dialog = search.dialog;
    await expect(dialog.getByText("FDD")).toBeVisible();
  });

  test("search results contain mock data names", async ({ page }) => {
    const search = new SearchPalettePage(page);
    await search.open();
    await search.search("Project");

    // Mock FDD deals include "Project Alpha" and "Project Beta"
    await search.expectResultContains("Project Alpha");
  });

  test("selecting a result navigates to the correct page", async ({ page }) => {
    const search = new SearchPalettePage(page);
    await search.open();
    await search.search("Project");

    // Wait for results then click the first one
    await expect(search.resultItems.first()).toBeVisible();
    await search.selectResult(0);

    // Dialog should close and URL should change
    await expect(search.dialog).toBeHidden();
    await expect(page).not.toHaveURL("/");
  });

  test("empty results show no-results message", async ({ page }) => {
    // Override search APIs to return empty results
    await page.route("**/api/fdd/deals*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );
    await page.route("**/api/kiis/search*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) }),
    );
    await page.route("**/api/im/documents*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) }),
    );

    const search = new SearchPalettePage(page);
    await search.open();
    await search.search("xyznonexistent");

    await expect(search.emptyState).toBeVisible();
  });
});
