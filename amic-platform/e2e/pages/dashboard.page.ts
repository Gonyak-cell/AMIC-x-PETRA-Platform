import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class DashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly kpiCards: Locator;
  readonly moduleStatus: Locator;
  readonly quickActions: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { level: 1 });
    this.kpiCards = page.locator("[class*='kpi'], [data-testid*='kpi']").or(
      page.getByText(/Active FDD Deals|Watchlist Alerts|IM In Progress|Draft Deals/),
    );
    this.moduleStatus = page.getByText(/Connected|Unreachable/);
    this.quickActions = page.getByText(
      /New Deal|New IM|Search Company|Watchlist/,
    );
  }

  async goto() {
    await this.page.goto("/");
  }

  async expectLoaded() {
    await expect(this.heading).toContainText(/Welcome/);
  }

  async navigateToModule(module: "fdd" | "kiis" | "im") {
    const routes: Record<string, string> = {
      fdd: "/fdd/deals",
      kiis: "/kiis",
      im: "/im",
    };
    await this.page.goto(routes[module]);
  }

  async openSearch() {
    await this.page.keyboard.press("Control+k");
  }
}
