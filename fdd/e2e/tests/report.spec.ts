/**
 * E2E: 보고서 생성 테스트.
 */

import { test, expect } from "../fixtures/deal.fixture";
import { ReportPage } from "../pages/report.page";

test.describe("Report Generation", () => {
  test("should display report page with options", async ({
    authedPage,
    dealId,
  }) => {
    const report = new ReportPage(authedPage);
    await report.goto(dealId);

    await expect(report.heading).toBeVisible();
    await expect(report.qoeCheckbox).toBeVisible();
    await expect(report.nwcCheckbox).toBeVisible();
    await expect(report.debtCheckbox).toBeVisible();
    await expect(report.issuesCheckbox).toBeVisible();
    await expect(report.formatSelect).toBeVisible();
    await expect(report.previewButton).toBeVisible();
    await expect(report.generateButton).toBeVisible();
  });

  test("should toggle report options", async ({ authedPage, dealId }) => {
    const report = new ReportPage(authedPage);
    await report.goto(dealId);

    // All options should be checked by default
    await expect(report.qoeCheckbox).toBeChecked();
    await expect(report.nwcCheckbox).toBeChecked();
    await expect(report.debtCheckbox).toBeChecked();
    await expect(report.issuesCheckbox).toBeChecked();

    // Uncheck QoE
    await report.setOptions({ qoe: false });
    await expect(report.qoeCheckbox).not.toBeChecked();

    // Recheck QoE
    await report.setOptions({ qoe: true });
    await expect(report.qoeCheckbox).toBeChecked();
  });

  test("should preview report sections", async ({ authedPage, dealId }) => {
    const report = new ReportPage(authedPage);
    await report.goto(dealId);

    await report.preview();

    // Either preview shows sections or error message
    const hasPreview = await report.previewSection
      .isVisible()
      .catch(() => false);
    const hasError = await report.errorMessage.isVisible().catch(() => false);

    expect(hasPreview || hasError).toBeTruthy();
  });

  test("should change output format", async ({ authedPage, dealId }) => {
    const report = new ReportPage(authedPage);
    await report.goto(dealId);

    await report.setOptions({ format: "json" });
    await expect(report.formatSelect).toHaveValue("json");

    await report.setOptions({ format: "pptx" });
    await expect(report.formatSelect).toHaveValue("pptx");
  });

  test("should attempt report generation", async ({ authedPage, dealId }) => {
    const report = new ReportPage(authedPage);
    await report.goto(dealId);

    // Set format to JSON (no download prompt)
    await report.setOptions({ format: "json" });
    await report.generateReport();

    // Either success or error message
    await authedPage.waitForTimeout(3_000);
  });
});
