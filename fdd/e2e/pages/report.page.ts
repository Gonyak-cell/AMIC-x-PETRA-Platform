import type { Page } from "@playwright/test";

export class ReportPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get heading() {
    return this.page.getByRole("heading", { name: /report generation/i });
  }
  get qoeCheckbox() {
    return this.page.getByText("Include QoE Analysis").locator("input[type='checkbox']");
  }
  get nwcCheckbox() {
    return this.page.getByText("Include NWC Analysis").locator("input[type='checkbox']");
  }
  get debtCheckbox() {
    return this.page.getByText("Include Net Debt Analysis").locator("input[type='checkbox']");
  }
  get issuesCheckbox() {
    return this.page.getByText("Include Issue Log").locator("input[type='checkbox']");
  }
  get formatSelect() {
    return this.page.locator("select").filter({ hasText: /powerpoint|json/i });
  }
  get previewButton() {
    return this.page.getByRole("button", { name: /preview/i });
  }
  get generateButton() {
    return this.page.getByRole("button", { name: /generate report/i });
  }
  get previewSection() {
    return this.page.getByText("Report Preview").locator("..");
  }
  get errorMessage() {
    return this.page.locator(".bg-red-50");
  }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}/report`);
  }

  async setOptions(opts: {
    qoe?: boolean;
    nwc?: boolean;
    debt?: boolean;
    issues?: boolean;
    format?: "pptx" | "json";
  }) {
    if (opts.qoe !== undefined) {
      const checked = await this.qoeCheckbox.isChecked();
      if (checked !== opts.qoe) await this.qoeCheckbox.click();
    }
    if (opts.nwc !== undefined) {
      const checked = await this.nwcCheckbox.isChecked();
      if (checked !== opts.nwc) await this.nwcCheckbox.click();
    }
    if (opts.debt !== undefined) {
      const checked = await this.debtCheckbox.isChecked();
      if (checked !== opts.debt) await this.debtCheckbox.click();
    }
    if (opts.issues !== undefined) {
      const checked = await this.issuesCheckbox.isChecked();
      if (checked !== opts.issues) await this.issuesCheckbox.click();
    }
    if (opts.format) {
      await this.formatSelect.selectOption(opts.format);
    }
  }

  async preview() {
    await this.previewButton.click();
    await this.page
      .waitForSelector("text=Report Preview", { timeout: 15_000 })
      .catch(() => {});
  }

  async generateReport() {
    await this.generateButton.click();
    await this.page.waitForTimeout(3_000);
  }

  async downloadPPT() {
    await this.formatSelect.selectOption("pptx");
    const downloadPromise = this.page.waitForEvent("download");
    await this.generateButton.click();
    return downloadPromise;
  }

  async getSectionCount() {
    const text = await this.page.getByText(/Sections:/).textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0], 10) : 0;
  }
}
