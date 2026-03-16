import { describe, it, expect } from "vitest";
import {
  buildRailOpenPath,
  buildRailClosePath,
} from "../workspace/railRouteHelpers";

describe("buildRailOpenPath", () => {
  it("기존 query를 유지하고 baseTab을 추가한다", () => {
    const params = new URLSearchParams("viewPhase=MARKETING&buyerId=b1");
    const result = buildRailOpenPath("txn-1", "risks", "buyers", params);

    expect(result).toBe(
      "/ma/transactions/txn-1/risks?viewPhase=MARKETING&buyerId=b1&baseTab=buyers",
    );
  });

  it("기존 query가 없으면 baseTab만 추가한다", () => {
    const params = new URLSearchParams();
    const result = buildRailOpenPath("txn-1", "timeline", "overview", params);

    expect(result).toBe("/ma/transactions/txn-1/timeline?baseTab=overview");
  });

  it("이미 baseTab이 있으면 덮어쓴다", () => {
    const params = new URLSearchParams("baseTab=old-tab&viewPhase=MARKETING");
    const result = buildRailOpenPath(
      "txn-1",
      "compliance",
      "contracts",
      params,
    );

    expect(result).toContain("baseTab=contracts");
    expect(result).not.toContain("baseTab=old-tab");
  });
});

describe("buildRailClosePath", () => {
  it("baseTab을 제거하고 나머지 query를 보존한다", () => {
    const params = new URLSearchParams(
      "baseTab=buyers&viewPhase=MARKETING&buyerId=b1",
    );
    const result = buildRailClosePath("txn-1", "buyers", params);

    expect(result).toBe(
      "/ma/transactions/txn-1/buyers?viewPhase=MARKETING&buyerId=b1",
    );
  });

  it("overview 복귀 시 빈 세그먼트 + trailing slash 방지", () => {
    const params = new URLSearchParams("baseTab=overview&viewPhase=MARKETING");
    const result = buildRailClosePath("txn-1", "overview", params);

    expect(result).toBe("/ma/transactions/txn-1?viewPhase=MARKETING");
    expect(result).not.toContain("//");
    expect(result).not.toMatch(/\/$/);
  });

  it("query가 baseTab뿐이면 query string 없이 반환한다", () => {
    const params = new URLSearchParams("baseTab=buyers");
    const result = buildRailClosePath("txn-1", "buyers", params);

    expect(result).toBe("/ma/transactions/txn-1/buyers");
    expect(result).not.toContain("?");
  });

  it("compose와 buyerId를 보존한다", () => {
    const params = new URLSearchParams(
      "baseTab=marketing-logs&buyerId=b1&compose=1&viewPhase=MARKETING",
    );
    const result = buildRailClosePath("txn-1", "marketing-logs", params);

    expect(result).toContain("buyerId=b1");
    expect(result).toContain("compose=1");
    expect(result).toContain("viewPhase=MARKETING");
    expect(result).not.toContain("baseTab");
  });
});
