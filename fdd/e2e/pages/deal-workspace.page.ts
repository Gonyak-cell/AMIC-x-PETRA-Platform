import type { Page } from "@playwright/test";

export class DealWorkspacePage {
  constructor(private page: Page) {}

  // ── Tab Navigation ──

  private tab(name: string) {
    return this.page.getByRole("link", { name, exact: false });
  }

  get overviewTab() { return this.tab("Overview"); }
  get definitionsTab() { return this.tab("Definitions"); }
  get uploadsTab() { return this.tab("Uploads"); }
  get mappingTab() { return this.tab("Mapping"); }
  get qoeTab() { return this.tab("QoE"); }
  get nwcTab() { return this.tab("NWC"); }
  get netDebtTab() { return this.tab("Net Debt"); }
  get issuesTab() { return this.tab("Issues"); }
  get reportTab() { return this.tab("Report"); }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}`);
  }

  async navigateToTab(tabName: string) {
    await this.tab(tabName).click();
  }

  async navigateToUploads(dealId: string) {
    await this.page.goto(`/deals/${dealId}/uploads`);
  }

  async navigateToMapping(dealId: string) {
    await this.page.goto(`/deals/${dealId}/mapping`);
  }

  async navigateToQoE(dealId: string) {
    await this.page.goto(`/deals/${dealId}/qoe`);
  }

  async navigateToNWC(dealId: string) {
    await this.page.goto(`/deals/${dealId}/nwc`);
  }

  async navigateToNetDebt(dealId: string) {
    await this.page.goto(`/deals/${dealId}/netdebt`);
  }

  async navigateToReport(dealId: string) {
    await this.page.goto(`/deals/${dealId}/report`);
  }

  /** Get the deal name from the workspace header. */
  async getDealName() {
    return this.page.locator("h1, h2").first().textContent();
  }
}
