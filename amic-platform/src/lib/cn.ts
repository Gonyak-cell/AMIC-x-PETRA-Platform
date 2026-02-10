/**
 * className 병합 유틸리티
 * Tailwind 클래스 조건부 조합에 사용
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
