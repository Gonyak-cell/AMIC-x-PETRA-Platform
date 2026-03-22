import type { AxiosError } from "axios";

/**
 * Axios error response에서 백엔드 detail 메시지를 추출한다.
 *
 * 지원하는 형태:
 * - RFC 7807: { detail: string }
 * - Pydantic validation: { detail: [{ msg: string, loc: [...] }] }
 * - Plain text fallback for non-HTML responses
 */
export function extractApiError(err: unknown, fallback: string): string {
  const axiosErr = err as AxiosError<{
    detail?: string | Array<{ msg: string }>;
  } | string>;
  const status = axiosErr?.response?.status;
  const responseData = axiosErr?.response?.data;
  const detail = typeof responseData === "string" ? undefined : responseData?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg).join(", ");
  }

  const raw = responseData;
  if (typeof raw === "string") {
    const text = raw.trim();
    if (
      text &&
      !/^<!doctype html/i.test(text) &&
      !/^<html/i.test(text) &&
      !/^internal server error$/i.test(text)
    ) {
      return text;
    }
  }

  if (status && status >= 500) {
    return `${fallback} (HTTP ${status})`;
  }

  return fallback;
}
