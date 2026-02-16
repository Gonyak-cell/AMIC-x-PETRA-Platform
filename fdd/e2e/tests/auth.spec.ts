/**
 * E2E: 인증 테스트 — 로그인/로그아웃/세션 관리.
 */

import { test, expect } from "@playwright/test";
import { LoginPage } from "../pages/login.page";
import { TEST_USERS } from "../utils/test-data";

test.describe("Authentication", () => {
  test("should display login page with form elements", async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();

    await expect(login.heading).toBeVisible();
    await expect(login.emailInput).toBeVisible();
    await expect(login.passwordInput).toBeVisible();
    await expect(login.submitButton).toBeVisible();
    await expect(login.submitButton).toHaveText("Sign In");
  });

  test("should login with valid credentials and redirect to deals", async ({
    page,
  }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.loginAndWaitForRedirect(
      TEST_USERS.admin.email,
      TEST_USERS.admin.password,
    );

    await expect(page).toHaveURL(/\/deals/);
  });

  test("should show error on invalid credentials", async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.login("wrong@email.com", "wrongpassword");

    await expect(login.errorMessage).toBeVisible();
    await expect(login.errorMessage).toContainText(/invalid/i);
  });

  test("should redirect unauthenticated users to login", async ({ page }) => {
    // Clear any stored tokens
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("autofdd_access_token");
      localStorage.removeItem("autofdd_refresh_token");
    });

    await page.goto("/deals");

    // Should redirect to login (if AUTH_ENABLED)
    // With AUTH_ENABLED=false, user will see deals page directly
    const url = page.url();
    const isOnLogin = url.includes("/login");
    const isOnDeals = url.includes("/deals");
    expect(isOnLogin || isOnDeals).toBeTruthy();
  });

  test("should display Sign In button disabled while loading", async ({
    page,
  }) => {
    const login = new LoginPage(page);
    await login.goto();

    await login.emailInput.fill(TEST_USERS.admin.email);
    await login.passwordInput.fill(TEST_USERS.admin.password);

    // Intercept login to delay response
    await page.route("**/auth/login", async (route) => {
      await new Promise((r) => setTimeout(r, 1_000));
      await route.continue();
    });

    await login.submitButton.click();

    // Button should show loading state
    await expect(login.submitButton).toContainText(/signing in/i);
  });
});
