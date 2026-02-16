import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class KiisDashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly kpiCards: Locator;
  readonly recentDealsCard: Locator;
  readonly riskCompaniesCard: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { name: "KIIS Dashboard" });
    this.kpiCards = page.locator("[class*='grid'] > div").first();
    this.recentDealsCard = page.getByText("Recent Deals").first();
    this.riskCompaniesCard = page.getByText("Risk Companies").first();
  }

  async goto() {
    await this.page.goto("/kiis");
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible();
  }

  async expectKpiVisible(label: string) {
    await expect(this.page.getByText(label).first()).toBeVisible();
  }

  async expectKpiValue(label: string, value: string) {
    const card = this.page.locator("div", { hasText: label }).filter({ hasText: value });
    await expect(card.first()).toBeVisible();
  }
}
