import { test, expect } from "@playwright/test";
import { LoginPage } from "../pages/login.page";

test.describe("Authentication", () => {
  test("redirects unauthenticated users to login", async ({ browser }) => {
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
    await context.close();
  });

  test("shows error for invalid credentials", async ({ browser }) => {
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login("invalid@test.com", "wrongpassword");
    await loginPage.expectLoginError();
    await context.close();
  });

  test("dashboard loads after successful login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      /Welcome/,
    );
  });

  test("logout redirects to login page", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Sign Out").click();
    await expect(page).toHaveURL(/\/login/);
  });
});
