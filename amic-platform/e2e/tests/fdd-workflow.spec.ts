import { test, expect } from "@playwright/test";
import { FddDealsPage } from "../pages/fdd-deals.page";

test.describe("FDD Workflow", () => {
  test("deal list page loads", async ({ page }) => {
    const dealsPage = new FddDealsPage(page);
    await dealsPage.goto();
    await dealsPage.expectDealListVisible();
  });

  test("new deal wizard page loads", async ({ page }) => {
    await page.goto("/fdd/deals/new");
    await expect(page).toHaveURL(/\/fdd\/deals\/new/);
    // Wizard form should be visible
    await expect(page.getByText(/deal name|create.*deal/i).first()).toBeVisible({
      timeout: 5000,
    });
  });

  test("navigating back from deal wizard returns to list", async ({ page }) => {
    await page.goto("/fdd/deals/new");
    await page.goBack();
    await expect(page).toHaveURL(/\/fdd\/deals/);
  });
});
