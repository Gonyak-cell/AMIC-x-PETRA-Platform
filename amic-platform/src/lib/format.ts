/**
 * 금액 포맷팅 (중복 코드 제거용 공통 유틸리티)
 * KRW: 소수점 없음, 천 단위 콤마
 * USD/EUR/JPY: 소수점 2자리 (또는 지정된 자릿수)
 */
export function formatAmount(
  value: number | string | null | undefined,
  currency?: string,
  decimals?: number
): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) {
    return "-";
  }

  // KRW는 소수점 없음
  const dp = decimals ?? (currency === "KRW" ? 0 : 2);

  // 음수 괄호 표기
  if (num < 0) {
    return `(${Math.abs(num).toLocaleString("en-US", {
      minimumFractionDigits: dp,
      maximumFractionDigits: dp,
    })})`;
  }

  return num.toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}

/**
 * 퍼센트 포맷팅
 */
export function formatPercent(
  value: number | string | null | undefined,
  decimals: number = 1
): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) {
    return "-";
  }

  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toFixed(decimals)}%`;
}

/**
 * 날짜 포맷팅 (YYYY-MM-DD → 읽기 좋은 형식)
 */
export function formatDate(
  value: string | null | undefined,
  format: "short" | "long" | "month" = "short"
): string {
  if (!value) return "-";

  const date = new Date(value);
  if (isNaN(date.getTime())) return "-";

  switch (format) {
    case "long":
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    case "month":
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
      });
    case "short":
    default:
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
  }
}

/**
 * 큰 숫자 축약 (1,000,000 → 1M)
 */
export function formatCompact(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "-";

  const absNum = Math.abs(num);

  if (absNum >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1)}B`;
  }
  if (absNum >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (absNum >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }

  return num.toFixed(0);
}
