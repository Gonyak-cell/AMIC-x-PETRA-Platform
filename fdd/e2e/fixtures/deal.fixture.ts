/**
 * Deal fixture — creates a deal before each test and cleans up after.
 *
 * Usage:
 *   import { test } from '../fixtures/deal.fixture';
 *   test('my test', async ({ authedPage, dealId }) => { ... });
 */

import { test as authTest } from "./auth.fixture";
import { createApiHelper } from "../utils/api-helper";
import { DEFAULT_DEAL, uniqueDealName } from "../utils/test-data";

type DealFixtures = {
  /** ID of a freshly created deal. */
  dealId: string;
};

export const test = authTest.extend<DealFixtures>({
  dealId: async ({ authToken, request }, use) => {
    const api = createApiHelper(request);
    const deal = await api.createDeal(authToken, {
      ...DEFAULT_DEAL,
      name: uniqueDealName(),
    });

    await use(deal.id);

    // Cleanup — best-effort delete
    try {
      await api.deleteDeal(authToken, deal.id);
    } catch {
      // Ignore cleanup errors
    }
  },
});

export { expect } from "@playwright/test";
