import { test, expect } from "@playwright/test";

test.describe("IM Workflow", () => {
  test("document list page loads", async ({ page }) => {
    await page.goto("/im");
    await expect(page).toHaveURL(/\/im/);
  });

  test("create document page loads", async ({ page }) => {
    await page.goto("/im/new");
    await expect(page).toHaveURL(/\/im\/new/);
  });

  test("templates page is accessible", async ({ page }) => {
    await page.goto("/im/templates");
    await expect(page).toHaveURL(/\/im\/templates/);
  });
});
