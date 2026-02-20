import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("sidebar module switching works", async ({ page }) => {
    await page.goto("/");
    const sidebar = page.locator("aside[role='navigation']");

    // Navigate to FDD
    await page.goto("/fdd/deals");
    await expect(sidebar.getByText("Deals")).toBeVisible();

    // Navigate to KIIS
    await page.goto("/kiis");
    await expect(sidebar.getByText("Companies")).toBeVisible();

    // Navigate to IM
    await page.goto("/im");
    await expect(sidebar.getByText("Projects")).toBeVisible();
  });

  test("global search opens with Ctrl+K", async ({ page }) => {
    await page.goto("/");

    // Open search
    await page.keyboard.press("Control+k");

    // Search palette should be visible
    await expect(
      page.getByPlaceholder(/search/i).or(page.getByRole("combobox")),
    ).toBeVisible({ timeout: 3000 });

    // Close with Escape
    await page.keyboard.press("Escape");
  });

  test("home link navigates to dashboard", async ({ page }) => {
    await page.goto("/fdd/deals");
    const sidebar = page.locator("aside[role='navigation']");
    await sidebar.getByText("Home").click();
    await expect(page).toHaveURL("/");
  });
});
