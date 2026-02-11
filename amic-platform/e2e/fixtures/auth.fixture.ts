import { test as base, expect } from "@playwright/test";

export const test = base.extend({});

export { expect };

/**
 * Global setup: login and save auth state for reuse.
 * Called once before all test suites via the "setup" project.
 */
export async function loginAndSaveState(
  page: ReturnType<typeof base.extend>,
  storageStatePath: string,
) {
  const email = process.env.TEST_USER_EMAIL ?? "admin@amic.test";
  const password = process.env.TEST_USER_PASSWORD ?? "testpassword123";

  // Navigate to login page
  await page.goto("/login");

  // Fill credentials
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in|login|log in/i }).click();

  // Wait for dashboard to load (successful login)
  await page.waitForURL("/", { timeout: 10_000 });

  // Save storage state (tokens in localStorage + cookies)
  await page.context().storageState({ path: storageStatePath });
}
