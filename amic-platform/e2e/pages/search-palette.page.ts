import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class SearchPalettePage {
  readonly page: Page;
  readonly dialog: Locator;
  readonly searchInput: Locator;
  readonly resultItems: Locator;
  readonly loadingText: Locator;
  readonly emptyState: Locator;
  readonly recentHeader: Locator;

  constructor(page: Page) {
    this.page = page;
    this.dialog = page.locator("[role='dialog'][aria-label='Global search']");
    this.searchInput = page.locator("[role='combobox'][aria-label='Search input']");
    this.resultItems = page.locator("[data-search-item]");
    this.loadingText = page.getByText("Searching...");
    this.emptyState = page.getByText(/No results found for/);
    this.recentHeader = page.getByText("Recent Searches");
  }

  async open() {
    await this.page.keyboard.press("Control+k");
    await expect(this.dialog).toBeVisible();
  }

  async close() {
    await this.page.keyboard.press("Escape");
    await expect(this.dialog).toBeHidden();
  }

  /** Type a query and wait for debounce + results to settle */
  async search(query: string) {
    await this.searchInput.fill(query);
    // Wait for search API response instead of fixed timeout
    await this.page.waitForResponse(
      (res) => res.url().includes("/api/") && res.url().includes("search"),
      { timeout: 5_000 },
    ).catch(() => {
      // Fallback: search may resolve from multiple endpoints
    });
    // Wait until loading finishes
    await expect(this.loadingText).toBeHidden({ timeout: 5_000 });
  }

  async expectResultCount(count: number) {
    await expect(this.resultItems).toHaveCount(count);
  }

  async expectResultContains(text: string) {
    await expect(this.page.locator("[data-search-item]", { hasText: text })).toBeVisible();
  }

  async selectResult(index: number) {
    await this.resultItems.nth(index).click();
  }
}
