import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class KiisCompaniesPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly searchInput: Locator;
  readonly marketFilter: Locator;
  readonly dataTable: Locator;
  readonly tableRows: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { level: 1 });
    this.searchInput = page.getByLabel("Search");
    this.marketFilter = page.getByLabel("Market");
    this.dataTable = page.locator("table");
    this.tableRows = page.locator("table tbody tr");
    this.emptyState = page.getByText("No companies found");
  }

  async goto() {
    await this.page.goto("/kiis/companies");
  }

  async expectLoaded() {
    await expect(this.heading).toContainText("Companies");
  }

  async expectCompanyVisible(name: string) {
    await expect(this.page.getByText(name).first()).toBeVisible();
  }

  async expectColumnHeaders(...headers: string[]) {
    for (const header of headers) {
      await expect(this.page.locator("th", { hasText: header })).toBeVisible();
    }
  }

  async searchFor(query: string) {
    await this.searchInput.fill(query);
  }
}
