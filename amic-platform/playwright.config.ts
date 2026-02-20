import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/tests",
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: process.env.CI ? 60_000 : 30_000,
  },
  projects: [
    {
      name: "setup",
      testMatch: /global-setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
    {
      name: "firefox",
      use: {
        ...devices["Desktop Firefox"],
        storageState: "e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
    {
      name: "chromium-mocked",
      testMatch: /.*-deep\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        // Block MSW service worker so page.route() can intercept API requests
        serviceWorkers: "block",
        storageState: {
          cookies: [],
          origins: [
            {
              origin: "http://localhost:5173",
              localStorage: [
                { name: "autofdd_access_token", value: "mock-token" },
              ],
            },
          ],
        },
      },
      // No setup dependency — api-mocks handles auth/me
    },
  ],
});
