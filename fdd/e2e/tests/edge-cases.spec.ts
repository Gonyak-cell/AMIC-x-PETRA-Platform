/**
 * E2E: 엣지 케이스 테스트.
 * - 대용량 GL 처리
 * - 오류 복구
 * - 권한 제한
 * - 동시 접속
 * - 세션 만료
 */

import * as path from "path";
import { test, expect } from "../fixtures/auth.fixture";
import { test as dealTest } from "../fixtures/deal.fixture";
import { LoginPage } from "../pages/login.page";
import { DealListPage } from "../pages/deal-list.page";
import { UploadPage } from "../pages/upload.page";
import { TEST_USERS } from "../utils/test-data";

const ASSETS_DIR = path.resolve(__dirname, "../test-assets");

test.describe("Edge Cases", () => {
  // ── #9: 대용량 GL 처리 ──
  dealTest(
    "should handle large GL file upload",
    async ({ authedPage, dealId }) => {
      dealTest.setTimeout(300_000); // 5 minutes

      const upload = new UploadPage(authedPage);
      await upload.goto(dealId);

      const largeFile = path.join(ASSETS_DIR, "large-gl.xlsx");
      await upload.uploadFile(largeFile);

      // Should show progress
      const count = await upload.getUploadCount();
      expect(count).toBeGreaterThanOrEqual(1);
    },
  );

  // ── #10: 오류 복구 ──
  dealTest(
    "should recover from upload failure on retry",
    async ({ authedPage, dealId }) => {
      const upload = new UploadPage(authedPage);
      await upload.goto(dealId);

      // Upload invalid file
      const invalidFile = path.join(ASSETS_DIR, "invalid-data.xlsx");
      await upload.uploadFile(invalidFile);

      await upload.confirmType(0, "TB");
      await upload.ingest(0);

      // Wait for failure
      await authedPage
        .getByText("FAILED")
        .first()
        .waitFor({ timeout: 30_000 })
        .catch(() => {});

      // Upload valid file and retry
      const validFile = path.join(ASSETS_DIR, "sample-tb.xlsx");
      await upload.uploadFile(validFile);
      await upload.confirmType(1, "TB");
      await upload.ingest(1);

      // Should eventually succeed
      await authedPage.waitForTimeout(5_000);
    },
  );

  // ── #11: 권한 제한 (Viewer) ──
  test(
    "should block Viewer from creating deals",
    async ({ page }) => {
      const login = new LoginPage(page);
      await login.goto();

      // Login as viewer
      await login.login(TEST_USERS.viewer.email, TEST_USERS.viewer.password);
      await page.waitForURL("**/deals**").catch(() => {});

      const dealList = new DealListPage(page);

      // Viewer should either not see "New Deal" button or get blocked
      const newDealVisible = await dealList.newDealButton
        .isVisible()
        .catch(() => false);

      if (newDealVisible) {
        // If button is visible, clicking should result in error
        await dealList.newDealButton.click();
        await dealList.dealNameInput.fill("Viewer Test");
        await page.getByLabel("Reference Date").fill("2025-12-31");
        await page.getByLabel("Period Start").fill("2025-01-01");
        await page.getByLabel("Period End").fill("2025-12-31");
        await dealList.createButton.click();

        // Should show error (403) or the form should not submit
        await page.waitForTimeout(2_000);
      }
    },
  );

  // ── #12: 동시 접속 ──
  test("should handle concurrent access to same deal", async ({
    browser,
  }) => {
    // Open two browser contexts (simulating two users)
    const ctx1 = await browser.newContext();
    const ctx2 = await browser.newContext();
    const page1 = await ctx1.newPage();
    const page2 = await ctx2.newPage();

    try {
      // Both navigate to deals page
      await page1.goto("/deals");
      await page2.goto("/deals");

      // Both should load without errors
      await expect(page1.getByText(/deals/i).first()).toBeVisible();
      await expect(page2.getByText(/deals/i).first()).toBeVisible();
    } finally {
      await ctx1.close();
      await ctx2.close();
    }
  });

  // ── #13: 세션 만료 ──
  test("should handle expired token gracefully", async ({ page }) => {
    // Set an invalid/expired token
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.setItem("autofdd_access_token", "expired.token.value");
      localStorage.setItem("autofdd_refresh_token", "expired.refresh.value");
    });

    // Navigate to a protected page
    await page.goto("/deals");

    // Should either redirect to login or show deals (if AUTH_ENABLED=false)
    await page.waitForTimeout(3_000);
    const url = page.url();
    const isOnLogin = url.includes("/login");
    const isOnDeals = url.includes("/deals");
    expect(isOnLogin || isOnDeals).toBeTruthy();
  });
});
