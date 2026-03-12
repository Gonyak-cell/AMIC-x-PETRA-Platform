import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * MA Transaction Workspace — Page Object Model
 *
 * 8-phase pipeline, PhaseActionPanel, tabs, hero actions를 캡슐화한다.
 */
export class MaWorkspacePage {
  readonly page: Page;

  // Hero
  readonly heading: Locator;
  readonly statusBadge: Locator;
  readonly phaseLabel: Locator;

  // Pipeline
  readonly pipelineSteps: Locator;

  // PhaseActionPanel
  readonly phasePanel: Locator;
  readonly prerequisites: Locator;
  readonly progressBar: Locator;
  readonly progressPercent: Locator;
  readonly gateSummary: Locator;
  readonly ackCheckboxes: Locator;
  readonly ackWarning: Locator;

  // Tabs
  readonly tabBar: Locator;

  // Hero actions
  readonly advanceButton: Locator;
  readonly rollbackButton: Locator;
  readonly holdButton: Locator;

  constructor(page: Page) {
    this.page = page;

    // Hero — PageHero renders h1 with the transaction name
    this.heading = page.locator("h1").first();
    this.statusBadge = page.locator("[class*='badge']").first();
    this.phaseLabel = page.getByText(/현재:/).first();

    // Pipeline — each step is rendered inside PipelineFlow
    this.pipelineSteps = page.locator("[data-phase]");

    // PhaseActionPanel — container with "현재 단계:" heading
    this.phasePanel = page
      .locator("div")
      .filter({ hasText: /^현재 단계:/ })
      .first();
    this.prerequisites = page.locator("ul li");
    this.progressBar = page.locator("[class*='bg-accent']").first();
    this.progressPercent = page.getByText(/%$/).first();
    this.gateSummary = page
      .locator("div")
      .filter({ hasText: /입찰 진입/ })
      .first();
    this.ackCheckboxes = page.locator("input[type='checkbox']");
    this.ackWarning = page.getByText(
      "단계 전환을 위해 확인이 필요한 항목이 있습니다",
    );

    // Tabs
    this.tabBar = page.locator("[role='tablist']").first();

    // Hero action buttons
    this.advanceButton = page.getByRole("button", { name: /단계로$/ });
    this.rollbackButton = page.getByRole("button", { name: /단계로$/ }).first();
    this.holdButton = page.getByRole("button", { name: "보류" });
  }

  async goto(txnId: string) {
    await this.page.goto(`/ma/transactions/${txnId}`);
  }

  async expectLoaded() {
    await expect(this.heading).toBeVisible({ timeout: 10_000 });
  }

  async clickTab(tabLabel: string) {
    await this.page.getByRole("tab", { name: tabLabel }).click();
  }

  async getVisibleTabLabels(): Promise<string[]> {
    const tabs = this.page.getByRole("tab");
    return tabs.allTextContents();
  }
}
