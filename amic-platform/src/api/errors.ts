import type { AxiosError } from "axios";

/**
 * Axios 에러에서 백엔드 detail 메시지를 추출한다.
 *
 * 지원 형태:
 * - RFC 7807: { detail: string }
 * - Pydantic validation: { detail: [{ msg: string, loc: [...] }] }
 */
export function extractApiError(err: unknown, fallback: string): string {
  const axiosErr = err as AxiosError<{
    detail?: string | Array<{ msg: string }>;
  }>;
  const status = axiosErr?.response?.status;
  // 5xx 서버 에러: 내부 메시지 노출 방지
  if (status && status >= 500) return fallback;
  const detail = axiosErr?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0)
    return detail.map((d) => d.msg).join(", ");
  return fallback;
}
