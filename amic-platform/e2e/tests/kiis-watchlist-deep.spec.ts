import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { KiisWatchlistPage } from "../pages/kiis-watchlist.page";

test.describe("KIIS Watchlist — Deep Data Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("watchlist page heading and sections render", async ({ page }) => {
    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();
    await watchlist.expectLoaded();

    await expect(watchlist.watchedCompaniesCard).toBeVisible();
    await expect(watchlist.alertHistoryCard).toBeVisible();
  });

  test("watched companies table renders from API", async ({ page }) => {
    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();
    await watchlist.expectLoaded();

    // mockWatchlistItems has 삼성전자 and SK하이닉스
    await watchlist.expectCompanyInWatchlist("삼성전자");
    await watchlist.expectCompanyInWatchlist("SK하이닉스");
  });

  test("alert type badges display correctly", async ({ page }) => {
    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();
    await watchlist.expectLoaded();

    // mockWatchlistItems[0] has alert_types: ["news", "disclosure"]
    await expect(page.getByText("news", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("disclosure", { exact: true }).first()).toBeVisible();
  });

  test("alert history table renders from API", async ({ page }) => {
    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();
    await watchlist.expectLoaded();

    // mockAlerts has "삼성전자 관련 뉴스" and "SK하이닉스 제재 알림"
    await watchlist.expectAlertVisible("삼성전자 관련 뉴스");
    await watchlist.expectAlertVisible("SK하이닉스 제재 알림");
  });

  test("unread count is shown in alert history header", async ({ page }) => {
    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();
    await watchlist.expectLoaded();

    // mockUnreadCount: { count: 3 }
    await watchlist.expectUnreadCount(3);
  });

  test("mark read button shown for unread alerts", async ({ page }) => {
    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();
    await watchlist.expectLoaded();

    // mockAlerts[0] is_read=false → "Mark read" button visible
    await expect(page.getByText("Mark read").first()).toBeVisible();
    // mockAlerts[1] is_read=true → "Read" text visible
    await expect(page.getByText("Read", { exact: true }).first()).toBeVisible();
  });

  test("empty state renders when no watchlist items", async ({ page }) => {
    await page.route("**/api/kiis/watchlist*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, items: [] }),
      }),
    );
    await page.route("**/api/kiis/alerts*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, page: 1, size: 20, items: [] }),
      }),
    );

    const watchlist = new KiisWatchlistPage(page);
    await watchlist.goto();

    await expect(watchlist.watchlistEmptyState).toBeVisible();
    await expect(watchlist.alertEmptyState).toBeVisible();
  });
});
