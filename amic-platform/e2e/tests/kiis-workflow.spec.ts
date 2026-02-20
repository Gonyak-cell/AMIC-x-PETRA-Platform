import { test, expect } from "@playwright/test";

test.describe("KIIS Workflow", () => {
  test("KIIS dashboard loads", async ({ page }) => {
    await page.goto("/kiis");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("companies page loads with list", async ({ page }) => {
    await page.goto("/kiis/companies");
    await expect(page).toHaveURL(/\/kiis\/companies/);
  });

  test("funds page loads", async ({ page }) => {
    await page.goto("/kiis/funds");
    await expect(page).toHaveURL(/\/kiis\/funds/);
  });

  test("watchlist page is accessible", async ({ page }) => {
    await page.goto("/kiis/watchlist");
    await expect(page).toHaveURL(/\/kiis\/watchlist/);
  });

  test("deal sourcing page loads", async ({ page }) => {
    await page.goto("/kiis/deals");
    await expect(page).toHaveURL(/\/kiis\/deals/);
  });
});
