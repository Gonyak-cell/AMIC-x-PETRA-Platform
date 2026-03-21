import { describe, expect, it } from "vitest";
import {
  buildProjectName,
  normalizeProjectSuffix,
  previewProjectCode,
} from "@/modules/ma/utils/projectName";

describe("projectName utilities", () => {
  it("preserves digits and hyphen while normalizing casing", () => {
    expect(normalizeProjectSuffix("tempus-01")).toBe("Tempus-01");
  });

  it("builds the canonical project name with prefix", () => {
    expect(buildProjectName("tempus-01")).toBe("Project Tempus-01");
  });

  it("builds a stable code preview from the normalized suffix", () => {
    const yy = new Date().getFullYear().toString().slice(2);
    expect(previewProjectCode("SE", "tempus-01")).toBe(`SE${yy}-TEM-??`);
  });
});
