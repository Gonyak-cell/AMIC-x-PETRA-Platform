import type { Page } from "@playwright/test";

export class DealListPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get heading() {
    return this.page.getByRole("heading", { name: "Deals" });
  }
  get newDealButton() {
    return this.page.getByRole("button", { name: /new deal/i });
  }
  get dealNameInput() {
    return this.page.getByPlaceholder("Project Alpha");
  }
  get dealTypeSelect() {
    return this.page.getByLabel("Deal Type");
  }
  get currencySelect() {
    return this.page.getByLabel("Currency");
  }
  get createButton() {
    return this.page.getByRole("button", { name: /create deal/i });
  }
  get cancelButton() {
    return this.page.getByRole("button", { name: /cancel/i });
  }

  // ── Actions ──

  async goto() {
    await this.page.goto("/deals");
  }

  async createDeal(opts: {
    name: string;
    type?: "COMPLETION_ACCOUNTS" | "LOCKED_BOX";
    currency?: string;
    referenceDate?: string;
    periodStart?: string;
    periodEnd?: string;
  }) {
    await this.newDealButton.click();
    await this.dealNameInput.fill(opts.name);

    if (opts.type) {
      await this.dealTypeSelect.selectOption(opts.type);
    }
    if (opts.currency) {
      await this.currencySelect.selectOption(opts.currency);
    }

    // Fill date fields
    const refDate = opts.referenceDate || "2025-12-31";
    const start = opts.periodStart || "2025-01-01";
    const end = opts.periodEnd || "2025-12-31";

    await this.page.getByLabel("Reference Date").fill(refDate);
    await this.page.getByLabel("Period Start").fill(start);
    await this.page.getByLabel("Period End").fill(end);

    await this.createButton.click();
    // Wait for the form to close (deal created)
    await this.page.waitForSelector("form", { state: "detached", timeout: 10_000 }).catch(() => {});
  }

  async getDealCards() {
    return this.page.locator("a[href^='/deals/']").all();
  }

  async clickDeal(dealName: string) {
    await this.page.getByText(dealName).click();
    await this.page.waitForURL("**/deals/**");
  }

  async getDealCount() {
    const cards = await this.getDealCards();
    return cards.length;
  }
}
