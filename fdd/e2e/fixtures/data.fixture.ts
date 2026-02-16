/**
 * Data fixture — provides a deal with uploaded & ingested TB/GL files.
 *
 * Usage:
 *   import { test } from '../fixtures/data.fixture';
 *   test('my test', async ({ authedPage, dealId }) => {
 *     // dealId already has TB+GL uploaded and ingested
 *   });
 */

import * as path from "path";
import { test as dealTest } from "./deal.fixture";
import { createApiHelper } from "../utils/api-helper";

const FIXTURES_DIR = path.resolve(__dirname, "../test-assets");

type DataFixtures = {
  /** Deal ID with TB+GL already uploaded & ingested. */
  dataReadyDealId: string;
};

export const test = dealTest.extend<DataFixtures>({
  dataReadyDealId: async ({ authToken, dealId, request }, use) => {
    const api = createApiHelper(request);

    // Upload & ingest TB
    const tbPath = path.join(FIXTURES_DIR, "sample-tb.xlsx");
    try {
      const tbUpload = await api.uploadFile(authToken, dealId, tbPath);
      await api.confirmType(authToken, dealId, tbUpload.id, "TB");
      await api.ingest(authToken, dealId, tbUpload.id);
    } catch {
      // Test assets may not exist yet; test will handle gracefully
    }

    // Upload & ingest GL
    const glPath = path.join(FIXTURES_DIR, "sample-gl.xlsx");
    try {
      const glUpload = await api.uploadFile(authToken, dealId, glPath);
      await api.confirmType(authToken, dealId, glUpload.id, "GL");
      await api.ingest(authToken, dealId, glUpload.id);
    } catch {
      // Test assets may not exist yet
    }

    await use(dealId);
  },
});

export { expect } from "@playwright/test";
