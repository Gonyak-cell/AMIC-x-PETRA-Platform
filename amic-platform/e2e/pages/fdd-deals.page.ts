import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class FddDealsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly dealList: Locator;
  readonly newDealButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { level: 1 });
    this.dealList = page.locator("table, [role='table']").or(
      page.getByText(/Deal|Name/).first(),
    );
    this.newDealButton = page
      .getByRole("link", { name: /new deal/i })
      .or(page.getByRole("button", { name: /new deal/i }));
  }

  async goto() {
    await this.page.goto("/fdd/deals");
  }

  async expectDealListVisible() {
    await expect(this.page).toHaveURL(/\/fdd\/deals/);
  }

  async createDeal() {
    await this.newDealButton.click();
    await expect(this.page).toHaveURL(/\/fdd\/deals\/new/);
  }

  async openDeal(dealName: string) {
    await this.page.getByText(dealName).click();
  }
}
