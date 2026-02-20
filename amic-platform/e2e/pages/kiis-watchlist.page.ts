import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class KiisWatchlistPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly watchedCompaniesCard: Locator;
  readonly alertHistoryCard: Locator;
  readonly watchlistTable: Locator;
  readonly alertTable: Locator;
  readonly watchlistEmptyState: Locator;
  readonly alertEmptyState: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { name: "Watchlist" });
    this.watchedCompaniesCard = page.getByText("Watched Companies").first();
    this.alertHistoryCard = page.getByText("Alert History").first();
    this.watchlistTable = page.locator("table").first();
    this.alertTable = page.locator("table").nth(1);
    this.watchlistEmptyState = page.getByText("Watchlist empty");
    this.alertEmptyState = page.getByText("No alerts");
  }

  async goto() {
    await this.page.goto("/kiis/watchlist");
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible();
  }

  async expectCompanyInWatchlist(name: string) {
    await expect(this.page.getByText(name).first()).toBeVisible();
  }

  async expectAlertVisible(title: string) {
    await expect(this.page.getByText(title).first()).toBeVisible();
  }

  async expectUnreadCount(count: number) {
    await expect(
      this.page.getByText(`${count} unread`).first(),
    ).toBeVisible();
  }
}
