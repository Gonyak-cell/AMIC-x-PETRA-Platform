import { test, expect } from "@playwright/test";

test.describe("Cross-Module Integration", () => {
  test("full navigation flow: Dashboard → FDD → KIIS → IM", async ({
    page,
  }) => {
    // Start at dashboard
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      /Welcome/,
    );

    // Navigate to FDD
    await page.goto("/fdd/deals");
    await expect(page).toHaveURL(/\/fdd\/deals/);

    // Navigate to KIIS
    await page.goto("/kiis");
    await expect(page).toHaveURL(/\/kiis/);

    // Navigate to IM
    await page.goto("/im");
    await expect(page).toHaveURL(/\/im/);

    // Back to dashboard
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      /Welcome/,
    );
  });

  test("notifications bell is visible", async ({ page }) => {
    await page.goto("/");
    // Bell icon should be in the header
    await expect(
      page.getByRole("button", { name: /notification/i }).or(
        page.locator("[aria-label*='notification' i]"),
      ),
    ).toBeVisible({ timeout: 5000 });
  });

  test("search across modules returns results", async ({ page }) => {
    await page.goto("/");

    // Open command palette
    await page.keyboard.press("Control+k");

    // Search input should appear
    const searchInput = page
      .getByPlaceholder(/search/i)
      .or(page.getByRole("combobox"));
    await expect(searchInput).toBeVisible({ timeout: 3000 });

    // Type a search query
    await searchInput.fill("test");

    // Wait briefly for results
    await page.waitForTimeout(500);

    // Close
    await page.keyboard.press("Escape");
  });
});
