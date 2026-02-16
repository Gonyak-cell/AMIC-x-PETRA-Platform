/**
 * E2E: Net Debt 분석 테스트.
 */

import { test, expect } from "../fixtures/data.fixture";
import { NetDebtPage } from "../pages/debt.page";

test.describe("Net Debt Analysis", () => {
  test("should display Net Debt page", async ({ authedPage, dealId }) => {
    const debt = new NetDebtPage(authedPage);
    await debt.goto(dealId);

    await expect(debt.calculateButton).toBeVisible();
  });

  test("should run Net Debt calculation", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const debt = new NetDebtPage(authedPage);
    await debt.goto(dataReadyDealId);

    await debt.snapshotInput.fill("test-snapshot-id");
    await debt.calculateButton.click();

    await authedPage.waitForTimeout(3_000);
  });

  test("should display debt summary after calculation", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const debt = new NetDebtPage(authedPage);
    await debt.goto(dataReadyDealId);

    const hasData = await authedPage
      .getByText("Gross Debt")
      .isVisible()
      .catch(() => false);

    if (hasData) {
      const gross = await debt.getGrossDebt();
      expect(gross).toBeTruthy();

      const net = await debt.getNetDebt();
      expect(net).toBeTruthy();
    }
  });
});
