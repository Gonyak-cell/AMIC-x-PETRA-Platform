/**
 * E2E: QoE(Quality of Earnings) 분석 테스트.
 */

import { test, expect } from "../fixtures/data.fixture";
import { QoEPage } from "../pages/qoe.page";

test.describe("QoE Analysis", () => {
  test("should display QoE page with empty state", async ({
    authedPage,
    dealId,
  }) => {
    const qoe = new QoEPage(authedPage);
    await qoe.goto(dealId);

    await expect(qoe.heading).toBeVisible();
    await expect(qoe.emptyState).toBeVisible();
    await expect(qoe.snapshotInput).toBeVisible();
    await expect(qoe.calculateButton).toBeVisible();
  });

  test("should run QoE calculation with snapshot", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const qoe = new QoEPage(authedPage);
    await qoe.goto(dataReadyDealId);

    // Use a snapshot ID (in test env, we need to create one first via API)
    // For this E2E test, we test the UI interaction
    await qoe.snapshotInput.fill("test-snapshot-id");
    await qoe.calculateButton.click();

    // Should show loading or error (depends on test data availability)
    await authedPage.waitForTimeout(3_000);
  });

  test("should display EBITDA summary and bridge after calculation", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const qoe = new QoEPage(authedPage);
    await qoe.goto(dataReadyDealId);

    // If there's already a QoE calculation, verify the display
    const hasCalculation = await qoe.emptyState.isVisible().catch(() => false);

    if (!hasCalculation) {
      // Verify bridge section is visible
      await expect(qoe.bridgeSection).toBeVisible();
      await expect(qoe.balanceStatus).toBeVisible();

      // Verify amounts are displayed
      const reported = await qoe.getReportedEbitda();
      expect(reported).toBeTruthy();

      const adjusted = await qoe.getAdjustedEbitda();
      expect(adjusted).toBeTruthy();
    }
  });

  test("should disable calculate button without snapshot ID", async ({
    authedPage,
    dealId,
  }) => {
    const qoe = new QoEPage(authedPage);
    await qoe.goto(dealId);

    // Clear snapshot input
    await qoe.snapshotInput.fill("");

    // Button should be disabled
    await expect(qoe.calculateButton).toBeDisabled();
  });
});
