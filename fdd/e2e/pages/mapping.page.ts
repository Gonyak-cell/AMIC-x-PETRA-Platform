import type { Page } from "@playwright/test";

export class MappingPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get heading() {
    return this.page.getByRole("heading", { name: "Account Mapping" });
  }
  get autoSuggestButton() {
    return this.page.getByRole("button", { name: /auto-suggest/i });
  }
  get saveAllButton() {
    return this.page.getByRole("button", { name: /save all/i });
  }
  get approveAllButton() {
    return this.page.getByRole("button", { name: /approve all/i });
  }
  get suggestionsTable() {
    return this.page.locator("table").first();
  }
  get mappingsTable() {
    return this.page.locator("table").nth(1);
  }
  get emptyState() {
    return this.page.getByText("No mappings yet");
  }
  get tieOutSection() {
    return this.page.getByText("Tie-out Results").locator("..");
  }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}/mapping`);
  }

  async runAutoSuggest() {
    await this.autoSuggestButton.click();
    // Wait for suggestions to appear (table with rows)
    await this.page.waitForSelector("text=Suggestions", { timeout: 30_000 });
  }

  async saveAllSuggestions() {
    await this.saveAllButton.click();
    // Wait for suggestions to clear
    await this.page.waitForTimeout(1_000);
  }

  async approveAll() {
    await this.approveAllButton.click();
    await this.page.waitForTimeout(1_000);
  }

  async approveSingle(mappingIndex: number) {
    const rows = this.page.locator("tbody tr");
    const row = rows.nth(mappingIndex);
    await row.getByRole("button", { name: /approve/i }).click();
  }

  async getSuggestionCount() {
    const header = this.page.getByText(/Suggestions \(\d+\)/);
    const text = await header.textContent();
    const match = text?.match(/\((\d+)\)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  async getMappingCount() {
    const header = this.page.getByText(/Saved Mappings \(\d+\)/);
    const text = await header.textContent();
    const match = text?.match(/\((\d+)\)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  async getTieOutStatus(statementType: "IS" | "BS") {
    const label =
      statementType === "IS" ? "Income Statement" : "Balance Sheet";
    const card = this.page.locator(`text=${label}`).locator("..").locator("..");
    const badge = card.locator(".rounded").last();
    return badge.textContent();
  }
}
