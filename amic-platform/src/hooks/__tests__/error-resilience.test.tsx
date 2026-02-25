/**
 * 훅 에러 복원력 테스트
 *
 * 백엔드 장애, API 응답 구조 변경 등 다양한 실패 시나리오에서
 * 프론트엔드 훅이 crash하지 않고 graceful하게 동작하는지 검증한다.
 */
import { toArray, safeStr } from "@/api/safe-parse";

// ── toArray 다양한 응답 형태 테스트 ─────────────────────────

describe("toArray — API 응답 형태별 복원력", () => {
  it("Deal[] 직접 배열 → 그대로 반환", () => {
    const deals = [
      { id: "1", name: "Deal A", status: "ACTIVE", created_at: "2026-01-01" },
    ];
    expect(toArray(deals)).toEqual(deals);
  });

  it("{items: Deal[]} 래핑 → items 추출", () => {
    const deals = [
      { id: "1", name: "Deal A", status: "ACTIVE", created_at: "2026-01-01" },
    ];
    expect(toArray({ items: deals, total: 1 })).toEqual(deals);
  });

  it("{data: Deal[]} 래핑 → data 추출", () => {
    const deals = [
      { id: "1", name: "Deal A", status: "ACTIVE", created_at: "2026-01-01" },
    ];
    expect(toArray({ data: deals })).toEqual(deals);
  });

  it("빈 응답 ({}) → 빈 배열 (crash 아님)", () => {
    expect(toArray({})).toEqual([]);
  });

  it("null 응답 → 빈 배열 (crash 아님)", () => {
    expect(toArray(null)).toEqual([]);
  });

  it("undefined 응답 → 빈 배열 (crash 아님)", () => {
    expect(toArray(undefined)).toEqual([]);
  });

  it("숫자 응답 → 빈 배열 (crash 아님)", () => {
    expect(toArray(42)).toEqual([]);
  });

  it("문자열 응답 → 빈 배열 (crash 아님)", () => {
    expect(toArray("error")).toEqual([]);
  });

  it("{items: null} → 빈 배열 (items가 null인 엣지 케이스)", () => {
    expect(toArray({ items: null })).toEqual([]);
  });

  it("{items: 'invalid'} → 빈 배열 (items가 배열이 아닌 경우)", () => {
    expect(toArray({ items: "not-an-array" })).toEqual([]);
  });

  it("{data: 123} → 빈 배열 (data가 배열이 아닌 경우)", () => {
    expect(toArray({ data: 123 })).toEqual([]);
  });
});

// ── safeStr 필드 접근 복원력 테스트 ─────────────────────────

describe("safeStr — 필드 접근 복원력", () => {
  it("정상 문자열 → 그대로 반환", () => {
    expect(safeStr("2026-01-15T10:00:00Z")).toBe("2026-01-15T10:00:00Z");
  });

  it("undefined → 빈 문자열 (slice crash 방지)", () => {
    expect(safeStr(undefined)).toBe("");
  });

  it("null → 빈 문자열", () => {
    expect(safeStr(null)).toBe("");
  });

  it("숫자 → 빈 문자열", () => {
    expect(safeStr(123)).toBe("");
  });

  it("fallback 값 사용", () => {
    expect(safeStr(undefined, "N/A")).toBe("N/A");
  });

  it("safeStr 후 .slice() 안전", () => {
    // created_at이 undefined인 deal 객체 시뮬레이션
    const deal = { id: "1", created_at: undefined as unknown as string };
    const dateStr = safeStr(deal.created_at).slice(0, 10);
    expect(dateStr).toBe("");
  });

  it("safeStr 후 정상 .slice()", () => {
    const deal = { id: "1", created_at: "2026-01-15T10:00:00Z" };
    const dateStr = safeStr(deal.created_at).slice(0, 10);
    expect(dateStr).toBe("2026-01-15");
  });
});

// ── 부분 실패 시나리오 테스트 ─────────────────────────

describe("부분 장애 시 데이터 격리", () => {
  it("toArray에 실패 응답을 넣어도 다른 데이터에 영향 없음", () => {
    // FDD는 정상, KIIS는 실패 시나리오
    const fddDeals = toArray([{ id: "1", name: "Deal A" }]);
    const kiisData = toArray(undefined); // KIIS 백엔드 다운

    expect(fddDeals).toHaveLength(1);
    expect(kiisData).toHaveLength(0);
    // 각각 독립적으로 처리됨
  });

  it("빈 배열에 .filter()/.map() 체이닝 안전", () => {
    const emptyResult = toArray(null);
    const filtered = emptyResult.filter((item: unknown) => item !== null);
    const mapped = emptyResult.map((item: unknown) => String(item));

    expect(filtered).toEqual([]);
    expect(mapped).toEqual([]);
  });
});
