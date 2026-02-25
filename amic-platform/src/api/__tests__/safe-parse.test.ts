/**
 * safe-parse 유틸리티 테스트
 *
 * API 응답 구조가 변경되어도 crash하지 않는지 검증한다.
 */
import { toArray, safeStr } from "@/api/safe-parse";

describe("toArray", () => {
  it("배열을 그대로 반환한다", () => {
    expect(toArray([1, 2, 3])).toEqual([1, 2, 3]);
  });

  it("{items: T[]} 형태에서 items를 추출한다", () => {
    expect(toArray({ items: [1, 2], total: 2 })).toEqual([1, 2]);
  });

  it("{data: T[]} 형태에서 data를 추출한다", () => {
    expect(toArray({ data: [1, 2] })).toEqual([1, 2]);
  });

  it("null → 빈 배열", () => {
    expect(toArray(null)).toEqual([]);
  });

  it("undefined → 빈 배열", () => {
    expect(toArray(undefined)).toEqual([]);
  });

  it("빈 객체 → 빈 배열", () => {
    expect(toArray({})).toEqual([]);
  });

  it("문자열 → 빈 배열", () => {
    expect(toArray("hello")).toEqual([]);
  });

  it("{items: null} → 빈 배열", () => {
    expect(toArray({ items: null })).toEqual([]);
  });

  it("{items: 'not-array'} → 빈 배열", () => {
    expect(toArray({ items: "not-array" })).toEqual([]);
  });
});

describe("safeStr", () => {
  it("문자열을 그대로 반환한다", () => {
    expect(safeStr("hello")).toBe("hello");
  });

  it("undefined → 빈 문자열", () => {
    expect(safeStr(undefined)).toBe("");
  });

  it("null → 빈 문자열", () => {
    expect(safeStr(null)).toBe("");
  });

  it("숫자 → 빈 문자열", () => {
    expect(safeStr(123)).toBe("");
  });

  it("fallback 값을 사용할 수 있다", () => {
    expect(safeStr(undefined, "N/A")).toBe("N/A");
  });
});
