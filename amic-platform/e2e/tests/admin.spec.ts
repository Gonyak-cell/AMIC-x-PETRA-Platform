import { test, expect } from "@playwright/test";

test.describe("Admin Features", () => {
  test("admin can access user management", async ({ page }) => {
    await page.goto("/admin/users");
    await expect(page).toHaveURL(/\/admin\/users/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("admin can access activity log", async ({ page }) => {
    await page.goto("/admin/activity");
    await expect(page).toHaveURL(/\/admin\/activity/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("admin can access analytics", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.getByText(/Cross-Module Analytics/)).toBeVisible();
  });

  test("settings profile page loads", async ({ page }) => {
    await page.goto("/settings/profile");
    await expect(page).toHaveURL(/\/settings\/profile/);
    await expect(page.getByText(/Profile & Settings/)).toBeVisible();
  });

  test("help center page loads", async ({ page }) => {
    await page.goto("/help");
    await expect(page).toHaveURL(/\/help/);
    await expect(page.getByText(/Help Center/)).toBeVisible();
  });

  test("calendar page loads", async ({ page }) => {
    await page.goto("/calendar");
    await expect(page).toHaveURL(/\/calendar/);
    await expect(page.getByText(/Calendar & Timeline/)).toBeVisible();
  });

  test("exports page loads", async ({ page }) => {
    await page.goto("/exports");
    await expect(page).toHaveURL(/\/exports/);
    await expect(page.getByText(/Data Export Hub/)).toBeVisible();
  });
});
