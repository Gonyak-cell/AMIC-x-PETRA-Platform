/**
 * API 응답 안전 파싱 유틸리티
 *
 * 백엔드 응답 구조가 변경되어도 프론트엔드가 crash하지 않도록 방어적 파싱을 제공한다.
 * 지원하는 응답 형태: T[], { items: T[] }, { data: T[] }, 기타 → 빈 배열
 */

/** 리스트 API 응답을 안전하게 배열로 변환한다. */
export function toArray<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    if ("items" in data && Array.isArray((data as { items: unknown }).items)) {
      return (data as { items: T[] }).items;
    }
    if ("data" in data && Array.isArray((data as { data: unknown }).data)) {
      return (data as { data: T[] }).data;
    }
  }
  return [];
}

/** 문자열 필드 안전 접근 — undefined/null/비문자열에서 .slice() crash 방지 */
export function safeStr(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}
