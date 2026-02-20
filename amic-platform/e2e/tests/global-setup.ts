import { test as setup } from "@playwright/test";
import { loginAndSaveState } from "../fixtures/auth.fixture";

const AUTH_FILE = "e2e/.auth/user.json";

setup("authenticate", async ({ page }) => {
  await loginAndSaveState(page, AUTH_FILE);
});
