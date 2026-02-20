import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class KiisNewsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly sourceFilter: Locator;
  readonly newsCards: Locator;
  readonly emptyState: Locator;
  readonly collectButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { name: "News" });
    this.sourceFilter = page.getByLabel("Source");
    this.newsCards = page.locator("button .space-y-2");
    this.emptyState = page.getByText("No news articles");
    this.collectButton = page.getByRole("button", { name: "Collect News" });
  }

  async goto() {
    await this.page.goto("/kiis/news");
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible();
  }

  async expectArticleVisible(title: string) {
    await expect(this.page.getByText(title).first()).toBeVisible();
  }

  async expectSourceBadgeVisible(source: string) {
    await expect(this.page.getByText(source, { exact: true }).first()).toBeVisible();
  }
}
