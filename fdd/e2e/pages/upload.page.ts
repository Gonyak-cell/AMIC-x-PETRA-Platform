import type { Page } from "@playwright/test";
import * as path from "path";

export class UploadPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get dropZone() {
    return this.page.locator(".border-dashed");
  }
  get fileInput() {
    return this.page.locator('input[type="file"]');
  }
  get selectFileButton() {
    return this.page.getByText("Select File");
  }

  /** Get all upload cards on the page. */
  uploadCards() {
    return this.page.locator(".bg-white.border.border-gray-border.rounded-lg.p-4");
  }

  // ── Actions ──

  async goto(dealId: string) {
    await this.page.goto(`/deals/${dealId}/uploads`);
  }

  async uploadFile(filePath: string) {
    await this.fileInput.setInputFiles(filePath);
    // Wait for upload card to appear
    await this.page.waitForSelector("text=PENDING", { timeout: 15_000 }).catch(() => {});
  }

  async confirmType(uploadIndex: number, type: string) {
    const card = this.uploadCards().nth(uploadIndex);
    const select = card.locator("select");
    await select.selectOption(type);
  }

  async ingest(uploadIndex: number) {
    const card = this.uploadCards().nth(uploadIndex);
    await card.getByRole("button", { name: /ingest/i }).click();
  }

  async waitForIngestComplete(uploadIndex: number) {
    const card = this.uploadCards().nth(uploadIndex);
    await card.getByText("COMPLETED").waitFor({ timeout: 60_000 });
  }

  async getUploadStatus(uploadIndex: number) {
    const card = this.uploadCards().nth(uploadIndex);
    const badge = card.locator(".rounded.text-xs.font-medium").first();
    return badge.textContent();
  }

  async getUploadCount() {
    return this.uploadCards().count();
  }

  async expandDetails(uploadIndex: number) {
    const card = this.uploadCards().nth(uploadIndex);
    await card.getByText("Details").click();
  }
}
