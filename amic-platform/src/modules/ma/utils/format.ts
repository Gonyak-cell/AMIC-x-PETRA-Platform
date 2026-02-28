/** 한국 원화 금액을 억/조 단위로 포맷팅 (음수 지원). */
export function formatKRW(value: number | null): string {
  if (value == null) return "-";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_000_000_000_000)
    return `${sign}${(abs / 1_000_000_000_000).toFixed(1)}조`;
  if (abs >= 100_000_000)
    return `${sign}${Math.round(abs / 100_000_000).toLocaleString()}억`;
  return `${sign}${Math.round(abs).toLocaleString()}`;
}

/** 매출액 간이 포맷 (null → "-", year 있으면 연도 접미사 표시, 음수 지원). */
export function formatRevenue(
  value: number | null,
  year?: number | null,
): string {
  if (value == null) return "-";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  const suffix = year ? ` (${year})` : "";
  if (abs >= 1_000_000_000_000)
    return `${sign}${(abs / 1_000_000_000_000).toFixed(1)}조${suffix}`;
  if (abs >= 100_000_000)
    return `${sign}${Math.round(abs / 100_000_000).toLocaleString()}억${suffix}`;
  return `${sign}${Math.round(abs).toLocaleString()}${suffix}`;
}

/** YYYYMMDD → YYYY.MM.DD 변환. */
export function formatDate(yyyymmdd: string): string {
  if (!yyyymmdd || yyyymmdd.length !== 8) return yyyymmdd || "-";
  return `${yyyymmdd.slice(0, 4)}.${yyyymmdd.slice(4, 6)}.${yyyymmdd.slice(6)}`;
}

/** ISO 날짜 문자열 → 한국어 날짜 (YYYY. MM. DD.) */
export function formatISODate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

/** 바이트 → 사람이 읽을 수 있는 크기 (B / KB / MB). */
export function formatFileSize(bytes: number | null): string {
  if (bytes == null || bytes === 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
