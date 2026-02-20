import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { KiisCompaniesPage } from "../pages/kiis-companies.page";

test.describe("KIIS Company List — Deep Data Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  test("company table renders company names from API", async ({ page }) => {
    const companies = new KiisCompaniesPage(page);
    await companies.goto();
    await companies.expectLoaded();

    // mockCompanies includes 삼성전자 and SK하이닉스
    await companies.expectCompanyVisible("삼성전자");
    await companies.expectCompanyVisible("SK하이닉스");
  });

  test("market badge shows KOSPI", async ({ page }) => {
    const companies = new KiisCompaniesPage(page);
    await companies.goto();
    await companies.expectLoaded();

    // Both companies have corp_cls: "Y" → KOSPI badge
    await expect(page.locator("table").getByText("KOSPI").first()).toBeVisible();
  });

  test("table shows expected column headers", async ({ page }) => {
    const companies = new KiisCompaniesPage(page);
    await companies.goto();
    await companies.expectLoaded();

    await companies.expectColumnHeaders("Company", "Stock Code", "Market", "CEO");
  });

  test("empty state renders when no companies match", async ({ page }) => {
    // Override companies to return empty result
    await page.route("**/api/kiis/companies*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 20 }),
      }),
    );

    const companies = new KiisCompaniesPage(page);
    await companies.goto();
    await expect(companies.emptyState).toBeVisible();
  });
});
