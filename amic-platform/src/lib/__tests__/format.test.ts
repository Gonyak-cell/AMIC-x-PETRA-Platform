import { formatAmount, formatPercent, formatDate, formatCompact } from "../format";

describe("formatAmount", () => {
  it("formats positive number with 2 decimals by default", () => {
    expect(formatAmount(1234567.89)).toBe("1,234,567.89");
  });

  it("formats KRW with no decimals", () => {
    expect(formatAmount(1500000, "KRW")).toBe("1,500,000");
  });

  it("formats USD with 2 decimals", () => {
    expect(formatAmount(1500, "USD")).toBe("1,500.00");
  });

  it("uses custom decimals when provided", () => {
    expect(formatAmount(1234.5678, "USD", 3)).toBe("1,234.568");
  });

  it("formats negative numbers with parentheses", () => {
    expect(formatAmount(-1500, "KRW")).toBe("(1,500)");
  });

  it('returns "-" for null', () => {
    expect(formatAmount(null)).toBe("-");
  });

  it('returns "-" for undefined', () => {
    expect(formatAmount(undefined)).toBe("-");
  });

  it('returns "-" for empty string', () => {
    expect(formatAmount("")).toBe("-");
  });

  it('returns "-" for NaN string', () => {
    expect(formatAmount("abc")).toBe("-");
  });

  it("parses string numbers", () => {
    expect(formatAmount("1234.56")).toBe("1,234.56");
  });

  it("formats zero correctly", () => {
    expect(formatAmount(0)).toBe("0.00");
  });
});

describe("formatPercent", () => {
  it("adds + sign for positive values", () => {
    expect(formatPercent(2.5)).toBe("+2.5%");
  });

  it("shows - sign for negative values", () => {
    expect(formatPercent(-1.3)).toBe("-1.3%");
  });

  it("shows 0.0% for zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
  });

  it("uses custom decimals", () => {
    expect(formatPercent(12.345, 2)).toBe("+12.35%");
  });

  it('returns "-" for null', () => {
    expect(formatPercent(null)).toBe("-");
  });

  it('returns "-" for undefined', () => {
    expect(formatPercent(undefined)).toBe("-");
  });

  it('returns "-" for NaN string', () => {
    expect(formatPercent("abc")).toBe("-");
  });

  it("parses string numbers", () => {
    expect(formatPercent("3.14")).toBe("+3.1%");
  });
});

describe("formatDate", () => {
  it('returns "-" for null', () => {
    expect(formatDate(null)).toBe("-");
  });

  it('returns "-" for undefined', () => {
    expect(formatDate(undefined)).toBe("-");
  });

  it('returns "-" for invalid date', () => {
    expect(formatDate("not-a-date")).toBe("-");
  });

  it("formats short date", () => {
    const result = formatDate("2025-06-15", "short");
    // ko-KR short format: YYYY. MM. DD.
    expect(result).toMatch(/2025/);
    expect(result).toMatch(/06|6/);
    expect(result).toMatch(/15/);
  });

  it("formats month date", () => {
    const result = formatDate("2025-06-15", "month");
    // ko-KR month format: "2025년 6월" or similar
    expect(result).toMatch(/2025/);
    expect(result).toMatch(/6/);
  });

  it("formats long date in Korean", () => {
    const result = formatDate("2025-06-15", "long");
    // ko-KR long format: YYYY년 M월 D일
    expect(result).toMatch(/2025/);
  });

  it("defaults to short format", () => {
    const result = formatDate("2025-01-01");
    // ko-KR: "2025. 01. 01." or similar
    expect(result).toMatch(/2025/);
    expect(result).toMatch(/01|1/);
  });
});

describe("formatCompact", () => {
  it("formats billions", () => {
    expect(formatCompact(1500000000)).toBe("1.5B");
  });

  it("formats millions", () => {
    expect(formatCompact(2500000)).toBe("2.5M");
  });

  it("formats thousands", () => {
    expect(formatCompact(1500)).toBe("1.5K");
  });

  it("shows raw number below 1000", () => {
    expect(formatCompact(999)).toBe("999");
  });

  it("handles negative billions", () => {
    expect(formatCompact(-1500000000)).toBe("-1.5B");
  });

  it('returns "-" for null', () => {
    expect(formatCompact(null)).toBe("-");
  });

  it('returns "-" for undefined', () => {
    expect(formatCompact(undefined)).toBe("-");
  });

  it('returns "-" for NaN string', () => {
    expect(formatCompact("abc")).toBe("-");
  });

  it("parses string numbers", () => {
    expect(formatCompact("5000000")).toBe("5.0M");
  });

  it("formats zero", () => {
    expect(formatCompact(0)).toBe("0");
  });
});
