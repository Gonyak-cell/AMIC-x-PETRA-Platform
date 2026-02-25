import type { Page, Locator } from "@playwright/test";

export class SidebarPage {
  readonly page: Page;
  readonly sidebar: Locator;
  readonly homeLink: Locator;
  readonly moduleSwitcher: Locator;

  constructor(page: Page) {
    this.page = page;
    this.sidebar = page.locator("aside[role='navigation']");
    this.homeLink = this.sidebar.getByText("Home");
    this.moduleSwitcher = this.sidebar.locator("[class*='ModuleSwitcher']").or(
      this.sidebar.getByText(/FDD|KIIS|IM/).first(),
    );
  }

  async navigateTo(label: string) {
    await this.sidebar.getByText(label, { exact: true }).click();
  }

  async switchModule(module: "ma" | "docs" | "kiis") {
    const labels: Record<string, string> = {
      ma: "M&A Deals",
      docs: "Deal Doc Studio",
      kiis: "KIIS",
    };
    await this.sidebar.getByText(labels[module]).click();
  }

  async expectAdminSectionVisible() {
    await this.sidebar.getByText("Admin").waitFor({ state: "visible" });
  }
}
