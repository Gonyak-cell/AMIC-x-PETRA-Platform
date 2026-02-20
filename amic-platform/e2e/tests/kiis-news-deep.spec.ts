import { test, expect } from "../fixtures/test-base";
import { mockAllApis, mockNewsList } from "../fixtures/api-mocks";
import { KiisNewsPage } from "../pages/kiis-news.page";

test.describe("KIIS News List — Deep Data Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("news heading and articles render", async ({ page }) => {
    const news = new KiisNewsPage(page);
    await news.goto();
    await news.expectLoaded();

    // mockNewsList has 3 articles
    await news.expectArticleVisible("삼성전자 반도체 실적 호조");
    await news.expectArticleVisible("SK하이닉스 HBM 수주 확대");
    await news.expectArticleVisible("바이오 산업 투자 동향 분석");
  });

  test("source badges display correctly", async ({ page }) => {
    const news = new KiisNewsPage(page);
    await news.goto();
    await news.expectLoaded();

    await news.expectSourceBadgeVisible("platum");
    await news.expectSourceBadgeVisible("dealsite");
  });

  test("source filter is present", async ({ page }) => {
    const news = new KiisNewsPage(page);
    await news.goto();
    await news.expectLoaded();

    await expect(news.sourceFilter).toBeVisible();
  });

  test("admin user sees Collect News button", async ({ page }) => {
    const news = new KiisNewsPage(page);
    await news.goto();
    await news.expectLoaded();

    // mockUser has role: "ADMIN"
    await expect(news.collectButton).toBeVisible();
  });

  test("empty state renders when no articles", async ({ page }) => {
    await page.route("**/api/kiis/news*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, page: 1, size: 20, items: [] }),
      }),
    );

    const news = new KiisNewsPage(page);
    await news.goto();
    await expect(news.emptyState).toBeVisible();
  });
});
