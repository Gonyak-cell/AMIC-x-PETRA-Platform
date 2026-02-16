import type { Page } from "@playwright/test";

export class NWCPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get heading() {
    return this.page.getByText(/net working capital/i);
  }
  get snapshotInput() {
    return this.page.getByPlaceholder("Snapshot ID");
  }
  get calculateButton() {
    return this.page.getByRole("button", { name: /calculate/i });
  }
  get summaryCard() {
    return this.page.getByText("Current Assets").locator("..").locator("..");
  }
  get lineItemsTable() {
    return this.page.locator("table").first();
  }
  get pegSimulationSection() {
    return this.page.getByText(/peg simulation/i).locator("..");
  }
  get trendSection() {
    return this.page.getByText(/monthly trend/i).locator("..");
  }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}/nwc`);
  }

  async runCalculation(snapshotId: string) {
    await this.snapshotInput.fill(snapshotId);
    await this.calculateButton.click();
    await this.page.waitForSelector("text=Current Assets", {
      timeout: 30_000,
    });
  }

  async changeClassification(itemIndex: number, classification: string) {
    const rows = this.lineItemsTable.locator("tbody tr");
    const select = rows.nth(itemIndex).locator("select");
    await select.selectOption(classification);
    await this.page.waitForTimeout(500);
  }

  async selectPegMethod(method: string) {
    const pegSelect = this.pegSimulationSection.locator("select");
    await pegSelect.selectOption(method);
  }

  async getCurrentAssets() {
    return this.page.getByText("Current Assets").locator("..").locator("dd, .font-mono").textContent();
  }

  async getCurrentLiabilities() {
    return this.page.getByText("Current Liabilities").locator("..").locator("dd, .font-mono").textContent();
  }

  async getNetWorkingCapital() {
    return this.page.getByText("Net Working Capital").locator("..").locator("dd, .font-mono").textContent();
  }
}
