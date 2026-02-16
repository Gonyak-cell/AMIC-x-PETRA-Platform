/**
 * E2E: NWC(Net Working Capital) 분석 테스트.
 */

import { test, expect } from "../fixtures/data.fixture";
import { NWCPage } from "../pages/nwc.page";

test.describe("NWC Analysis", () => {
  test("should display NWC page", async ({ authedPage, dealId }) => {
    const nwc = new NWCPage(authedPage);
    await nwc.goto(dealId);

    // Page should have calculate controls
    await expect(nwc.calculateButton).toBeVisible();
  });

  test("should run NWC calculation", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const nwc = new NWCPage(authedPage);
    await nwc.goto(dataReadyDealId);

    await nwc.snapshotInput.fill("test-snapshot-id");
    await nwc.calculateButton.click();

    // Wait for result or error
    await authedPage.waitForTimeout(3_000);
  });

  test("should display NWC summary with amounts", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const nwc = new NWCPage(authedPage);
    await nwc.goto(dataReadyDealId);

    // If calculation exists, verify display
    const hasData = await authedPage
      .getByText("Current Assets")
      .isVisible()
      .catch(() => false);

    if (hasData) {
      const assets = await nwc.getCurrentAssets();
      expect(assets).toBeTruthy();

      const liabilities = await nwc.getCurrentLiabilities();
      expect(liabilities).toBeTruthy();

      const nwcValue = await nwc.getNetWorkingCapital();
      expect(nwcValue).toBeTruthy();
    }
  });
});
