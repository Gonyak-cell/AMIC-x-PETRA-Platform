/**
 * 금액 포맷팅 (중복 코드 제거용 공통 유틸리티)
 * KRW: 소수점 없음, 천 단위 콤마
 * USD/EUR: 소수점 2자리, JPY: 소수점 없음 (또는 지정된 자릿수)
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
  if (!isFinite(num)) {
    return "-";
  }

  // KRW/JPY는 소수점 없음
  const dp = decimals ?? (currency === "KRW" || currency === "JPY" ? 0 : 2);

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
  if (!isFinite(num)) {
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
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "short",
      });
    case "short":
    default:
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
  }
}

/**
 * 파일 크기 포맷팅 (bytes → human-readable)
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * 한국 원화 대금액 축약 (조/억/만 단위)
 * 206,875,789,000,000 → "206.9조"
 * 55,277,053,000,000 → "55.3조"
 * 1,234,567,890 → "12.3억"
 */
export function formatAmountKRW(
  value: number | string | null | undefined,
): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(num)) return "-";

  const absNum = Math.abs(num);
  const sign = num < 0 ? "-" : "";

  if (absNum >= 1_000_000_000_000) {
    return `${sign}${(absNum / 1_000_000_000_000).toFixed(1)}조`;
  }
  if (absNum >= 100_000_000) {
    return `${sign}${Math.round(absNum / 100_000_000).toLocaleString("en-US")}억`;
  }
  if (absNum >= 10_000) {
    return `${sign}${Math.round(absNum / 10_000).toLocaleString("en-US")}만`;
  }

  return num.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

/**
 * 큰 숫자 축약 (1,000,000 → 1M)
 */
export function formatCompact(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(num)) return "-";

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

/**
 * KPI 카드용 금액 축약 (통화 자동 판별)
 * KRW/JPY → 조/억/만 단위, USD/EUR 등 → B/M/K 단위
 */
export function formatAmountCompact(
  value: number | string | null | undefined,
  currency?: string,
): string {
  if (value === null || value === undefined || value === "") return "-";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(num)) return "-";

  if (currency === "KRW" || currency === "JPY") {
    return formatAmountKRW(num);
  }
  return formatCompact(num);
}
