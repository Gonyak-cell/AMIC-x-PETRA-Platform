import { describe, expect, it } from "vitest";

import { getModuleErrorMessage } from "../analyticsKpiErrorMessage";

describe("getModuleErrorMessage", () => {
  it("maps 401 errors to a session access message", () => {
    expect(
      getModuleErrorMessage("FDD", {
        kind: "unauthorized",
        status: 401,
      }),
    ).toContain("현재 세션에서는 조회할 수 없습니다");
  });

  it("maps 403 errors to a forbidden message", () => {
    expect(
      getModuleErrorMessage("KIIS", {
        kind: "forbidden",
        status: 403,
      }),
    ).toContain("조회 권한이 없습니다");
  });

  it("keeps unreachable errors as backend connectivity issues", () => {
    expect(
      getModuleErrorMessage("IM", {
        kind: "unreachable",
      }),
    ).toContain("backend is unreachable");
  });
});
