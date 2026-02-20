import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class ImDocumentsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly dataTable: Locator;
  readonly tableRows: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { level: 1 });
    this.dataTable = page.locator("table");
    this.tableRows = page.locator("table tbody tr");
    this.emptyState = page.getByText("No IM projects yet");
  }

  async goto() {
    await this.page.goto("/im");
  }

  async expectLoaded() {
    await expect(this.heading).toContainText("IM Projects");
  }

  async expectDocumentVisible(name: string) {
    await expect(this.page.getByText(name).first()).toBeVisible();
  }

  async expectKpiValue(label: string, value: string) {
    // Use first() to target KPI card (before table which may also contain the label text)
    const card = this.page.getByText(label).first().locator("../..");
    await expect(card).toContainText(value);
  }
}
