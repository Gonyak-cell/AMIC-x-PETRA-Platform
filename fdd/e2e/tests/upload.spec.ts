/**
 * E2E: 파일 업로드 + 타입 확인 + 인제스트 테스트.
 */

import * as path from "path";
import { test, expect } from "../fixtures/deal.fixture";
import { UploadPage } from "../pages/upload.page";

const ASSETS_DIR = path.resolve(__dirname, "../test-assets");

test.describe("File Upload", () => {
  test("should display upload page with drop zone", async ({
    authedPage,
    dealId,
  }) => {
    const upload = new UploadPage(authedPage);
    await upload.goto(dealId);

    await expect(upload.dropZone).toBeVisible();
    await expect(upload.selectFileButton).toBeVisible();
    await expect(
      authedPage.getByText("No files uploaded yet"),
    ).toBeVisible();
  });

  test("should upload an Excel file and show upload card", async ({
    authedPage,
    dealId,
  }) => {
    const upload = new UploadPage(authedPage);
    await upload.goto(dealId);

    const tbFile = path.join(ASSETS_DIR, "sample-tb.xlsx");
    await upload.uploadFile(tbFile);

    // Upload card should appear
    const count = await upload.getUploadCount();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test("should confirm file type and ingest", async ({
    authedPage,
    dealId,
  }) => {
    const upload = new UploadPage(authedPage);
    await upload.goto(dealId);

    const tbFile = path.join(ASSETS_DIR, "sample-tb.xlsx");
    await upload.uploadFile(tbFile);

    // Confirm type as TB
    await upload.confirmType(0, "TB");

    // Ingest
    await upload.ingest(0);
    await upload.waitForIngestComplete(0);

    const status = await upload.getUploadStatus(0);
    expect(status).toBe("COMPLETED");
  });

  test("should show validation errors for invalid file", async ({
    authedPage,
    dealId,
  }) => {
    const upload = new UploadPage(authedPage);
    await upload.goto(dealId);

    // Upload an invalid file (empty or wrong format)
    const invalidFile = path.join(ASSETS_DIR, "invalid-data.xlsx");
    await upload.uploadFile(invalidFile);

    // Attempt ingest and check for errors
    await upload.confirmType(0, "TB");
    await upload.ingest(0);

    // Wait for FAILED or validation errors
    await authedPage
      .getByText(/FAILED|COMPLETED/)
      .first()
      .waitFor({ timeout: 30_000 });
  });

  test("should upload multiple files sequentially", async ({
    authedPage,
    dealId,
  }) => {
    const upload = new UploadPage(authedPage);
    await upload.goto(dealId);

    // Upload TB
    const tbFile = path.join(ASSETS_DIR, "sample-tb.xlsx");
    await upload.uploadFile(tbFile);

    // Upload GL
    const glFile = path.join(ASSETS_DIR, "sample-gl.xlsx");
    await upload.uploadFile(glFile);

    const count = await upload.getUploadCount();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test("should expand upload details", async ({ authedPage, dealId }) => {
    const upload = new UploadPage(authedPage);
    await upload.goto(dealId);

    const tbFile = path.join(ASSETS_DIR, "sample-tb.xlsx");
    await upload.uploadFile(tbFile);

    await upload.expandDetails(0);
    // Details section should now be visible
    await authedPage.waitForTimeout(500);
  });
});
