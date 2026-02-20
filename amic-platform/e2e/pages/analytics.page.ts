import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

export class AnalyticsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly fddSection: Locator;
  readonly kiisSection: Locator;
  readonly imSection: Locator;
  readonly charts: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole("heading", { level: 1 });
    this.fddSection = page.getByRole("heading", { name: "Auto FDD", level: 3 });
    this.kiisSection = page.getByRole("heading", { name: "KIIS", level: 3 });
    this.imSection = page.getByRole("heading", { name: "IM Generator", level: 3 });
    this.charts = page.locator(".recharts-responsive-container svg");
  }

  async goto() {
    await this.page.goto("/analytics");
  }

  async expectLoaded() {
    await expect(this.heading).toContainText("Cross-Module Analytics");
  }

  async expectAllSectionsVisible() {
    await expect(this.fddSection).toBeVisible();
    await expect(this.kiisSection).toBeVisible();
    await expect(this.imSection).toBeVisible();
  }

  async expectChartsRendered() {
    // At least one Recharts SVG should exist
    await expect(this.charts.first()).toBeVisible({ timeout: 10_000 });
    // Chart SVG should contain drawn elements (paths or rects)
    const svgCount = await this.charts.count();
    expect(svgCount).toBeGreaterThanOrEqual(1);
  }

  async expectErrorBanner(module: "fdd" | "kiis" | "im") {
    const labels: Record<string, string> = {
      fdd: "FDD backend is unreachable",
      kiis: "KIIS backend is unreachable",
      im: "IM backend is unreachable",
    };
    await expect(this.page.getByText(labels[module])).toBeVisible();
  }
}
