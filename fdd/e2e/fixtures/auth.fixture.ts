/**
 * Auth fixture — provides pre-authenticated page and API token.
 *
 * Usage:
 *   import { test } from '../fixtures/auth.fixture';
 *   test('my test', async ({ authedPage, authToken }) => { ... });
 */

import { test as base, type Page } from "@playwright/test";
import { TEST_USERS } from "../utils/test-data";
import { createApiHelper } from "../utils/api-helper";

type AuthFixtures = {
  /** Page already logged in as admin. */
  authedPage: Page;
  /** Raw JWT access token for API helper calls. */
  authToken: string;
};

export const test = base.extend<AuthFixtures>({
  authedPage: async ({ page, request }, use) => {
    const api = createApiHelper(request);
    const user = TEST_USERS.admin;

    // Try API login first; if AUTH_ENABLED=false we can skip
    try {
      const token = await api.login(user.email, user.password);
      // Set token in localStorage before navigating
      await page.goto("/");
      await page.evaluate(
        ({ access, refresh }) => {
          localStorage.setItem("autofdd_access_token", access);
          localStorage.setItem("autofdd_refresh_token", refresh || access);
        },
        { access: token, refresh: token },
      );
      await page.goto("/deals");
    } catch {
      // AUTH_ENABLED=false — navigate directly
      await page.goto("/deals");
    }

    await use(page);
  },

  authToken: async ({ request }, use) => {
    const api = createApiHelper(request);
    try {
      const token = await api.login(
        TEST_USERS.admin.email,
        TEST_USERS.admin.password,
      );
      await use(token);
    } catch {
      // AUTH_ENABLED=false — use empty token
      await use("");
    }
  },
});

export { expect } from "@playwright/test";
