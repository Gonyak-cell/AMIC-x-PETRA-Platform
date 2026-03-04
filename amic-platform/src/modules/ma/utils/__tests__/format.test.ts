import { describe, it, expect } from "vitest";
import { formatBillions } from "../format";

describe("formatBillions", () => {
  it("null → 대시", () => {
    expect(formatBillions(null)).toBe("-");
  });

  it("NaN 문자열 → 대시", () => {
    expect(formatBillions("abc")).toBe("-");
  });

  it("0 → 0억", () => {
    expect(formatBillions(0)).toBe("0억");
  });

  it("일반 억원 값 → 콤마 포맷 + 억", () => {
    expect(formatBillions(500)).toBe("500억");
    expect(formatBillions(9999)).toBe("9,999억");
  });

  it("10000 이상 → 조 단위 변환", () => {
    expect(formatBillions(10000)).toBe("1.0조");
    expect(formatBillions(15000)).toBe("1.5조");
    expect(formatBillions(100000)).toBe("10.0조");
  });

  it("문자열 숫자 입력 → 정상 파싱", () => {
    expect(formatBillions("500")).toBe("500억");
    expect(formatBillions("15000")).toBe("1.5조");
  });

  it("소수점 입력 → 반올림 포맷", () => {
    expect(formatBillions("1234.56")).toBe("1,235억");
    expect(formatBillions(999.4)).toBe("999억");
  });

  it("경계값 9999.5 → 조 변환 아닌 억 포맷", () => {
    expect(formatBillions(9999.5)).toBe("10,000억");
  });
});
