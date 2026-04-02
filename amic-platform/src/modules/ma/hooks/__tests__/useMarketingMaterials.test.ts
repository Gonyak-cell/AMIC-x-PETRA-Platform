import { describe, expect, it } from "vitest";

import { buildMarketingMaterialUploadErrorMessage } from "../useMarketingMaterials";

describe("useMarketingMaterials helpers", () => {
  it("keeps backend detail for upload validation failures", () => {
    const err = {
      response: {
        status: 400,
        data: {
          detail: "Multiple file extensions are not allowed.",
        },
      },
    };

    expect(buildMarketingMaterialUploadErrorMessage(err, "TM")).toBe(
      "Multiple file extensions are not allowed.",
    );
  });

  it("falls back to the TM upload message when detail is unavailable", () => {
    const err = {
      response: {
        status: 500,
        data: "Internal Server Error",
      },
    };

    expect(buildMarketingMaterialUploadErrorMessage(err, "TM")).toBe(
      "Teaser 업로드에 실패했습니다. 잠시 후 다시 시도해 주세요. (HTTP 500)",
    );
  });
});
