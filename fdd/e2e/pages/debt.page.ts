import type { Page } from "@playwright/test";

export class NetDebtPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get heading() {
    return this.page.getByText(/net debt/i).first();
  }
  get snapshotInput() {
    return this.page.getByPlaceholder("Snapshot ID");
  }
  get calculateButton() {
    return this.page.getByRole("button", { name: /calculate/i });
  }
  get recalculateButton() {
    return this.page.getByRole("button", { name: /recalculate/i });
  }
  get summaryCard() {
    return this.page.getByText("Gross Debt").locator("..").locator("..");
  }
  get bridgeTable() {
    return this.page.locator("table").first();
  }
  get debtItemsTable() {
    return this.page.locator("table").nth(1);
  }
  get addItemForm() {
    return this.page.getByText(/add.*item/i).locator("..");
  }
  get ifrs16Checkbox() {
    return this.page.getByText(/ifrs 16/i).locator("input[type='checkbox']");
  }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}/netdebt`);
  }

  async runCalculation(snapshotId: string) {
    await this.snapshotInput.fill(snapshotId);
    await this.calculateButton.click();
    await this.page.waitForSelector("text=Gross Debt", { timeout: 30_000 });
  }

  async addManualItem(type: string, description: string, amount: string) {
    const form = this.addItemForm;
    await form.locator("select").selectOption(type);
    await form.getByPlaceholder(/description/i).fill(description);
    await form.getByPlaceholder(/amount/i).fill(amount);
    await form.getByRole("button", { name: /add/i }).click();
    await this.page.waitForTimeout(500);
  }

  async approveItem(index: number) {
    const rows = this.debtItemsTable.locator("tbody tr");
    await rows.nth(index).getByRole("button", { name: /approve/i }).click();
    await this.page.waitForTimeout(500);
  }

  async recalculate() {
    await this.recalculateButton.click();
    await this.page.waitForTimeout(2_000);
  }

  async toggleIFRS16() {
    await this.ifrs16Checkbox.click();
    await this.page.waitForTimeout(500);
  }

  async getGrossDebt() {
    return this.page.getByText("Gross Debt").locator("..").locator(".font-mono, dd").textContent();
  }

  async getNetDebt() {
    return this.page.getByText("Net Debt").locator("..").locator(".font-mono, dd").first().textContent();
  }
}
