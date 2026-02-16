import type { Page } from "@playwright/test";

export class QoEPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get heading() {
    return this.page.getByRole("heading", {
      name: /quality of earnings/i,
    });
  }
  get snapshotInput() {
    return this.page.getByPlaceholder("Snapshot ID");
  }
  get calculateButton() {
    return this.page.getByRole("button", { name: /calculate qoe/i });
  }
  get recalculateButton() {
    return this.page.getByRole("button", { name: /recalculate/i });
  }
  get bridgeSection() {
    return this.page.getByText("QoE Bridge").locator("..");
  }
  get ebitdaSummary() {
    return this.page.getByText("Income Statement").locator("..");
  }
  get candidatesSection() {
    return this.page.getByText(/adjustment candidates/i).locator("..");
  }
  get balanceStatus() {
    return this.page
      .locator("span")
      .filter({ hasText: /balanced|imbalanced/i });
  }
  get emptyState() {
    return this.page.getByText("No QoE calculation found");
  }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}/qoe`);
  }

  async runCalculation(snapshotId: string) {
    await this.snapshotInput.fill(snapshotId);
    await this.calculateButton.click();
    // Wait for bridge to appear
    await this.page.waitForSelector("text=QoE Bridge", { timeout: 30_000 });
  }

  async recalculate() {
    await this.recalculateButton.click();
    await this.page.waitForTimeout(2_000);
  }

  async approveAdjustment(index: number) {
    const rows = this.candidatesSection.locator("tbody tr");
    await rows.nth(index).getByRole("button", { name: /approve/i }).click();
    await this.page.waitForTimeout(500);
  }

  async getReportedEbitda() {
    const row = this.page.getByText("Reported EBITDA").locator("..");
    const amount = row.locator(".tabular-nums, .text-right").last();
    return amount.textContent();
  }

  async getAdjustedEbitda() {
    const row = this.page.getByText("Adjusted EBITDA").locator("..");
    const amount = row.locator(".tabular-nums, .text-right").last();
    return amount.textContent();
  }

  async getCandidateCount() {
    const header = this.page.getByText(/Adjustment Candidates \(\d+\)/);
    const text = await header.textContent();
    const match = text?.match(/\((\d+)\)/);
    return match ? parseInt(match[1], 10) : 0;
  }
}
