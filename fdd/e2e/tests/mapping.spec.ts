/**
 * E2E: 계정 매핑 테스트 — 자동 제안 → 저장 → 승인 → Tie-out.
 */

import { test, expect } from "../fixtures/data.fixture";
import { MappingPage } from "../pages/mapping.page";

test.describe("Account Mapping", () => {
  test("should display mapping page with empty state", async ({
    authedPage,
    dealId,
  }) => {
    const mapping = new MappingPage(authedPage);
    await mapping.goto(dealId);

    await expect(mapping.heading).toBeVisible();
    await expect(mapping.autoSuggestButton).toBeVisible();
  });

  test("should run auto-suggest mappings", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const mapping = new MappingPage(authedPage);
    await mapping.goto(dataReadyDealId);

    await mapping.runAutoSuggest();

    // Suggestions should appear
    const count = await mapping.getSuggestionCount();
    expect(count).toBeGreaterThan(0);
  });

  test("should save suggestions as proposed mappings", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const mapping = new MappingPage(authedPage);
    await mapping.goto(dataReadyDealId);

    await mapping.runAutoSuggest();
    await mapping.saveAllSuggestions();

    // Saved mappings should appear
    const count = await mapping.getMappingCount();
    expect(count).toBeGreaterThan(0);
  });

  test("should approve all proposed mappings", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const mapping = new MappingPage(authedPage);
    await mapping.goto(dataReadyDealId);

    await mapping.runAutoSuggest();
    await mapping.saveAllSuggestions();
    await mapping.approveAll();

    // All mappings should be APPROVED
    await expect(
      authedPage.getByText("APPROVED").first(),
    ).toBeVisible();
  });

  test("should display tie-out results after mapping", async ({
    authedPage,
    dataReadyDealId,
  }) => {
    const mapping = new MappingPage(authedPage);
    await mapping.goto(dataReadyDealId);

    // Check tie-out section exists
    await expect(mapping.tieOutSection).toBeVisible();
  });
});
