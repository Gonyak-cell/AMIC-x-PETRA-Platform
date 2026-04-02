import type { AxiosError } from "axios";

import { extractApiError } from "@/api/errors";

export const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";
export const DEV_MA_PROXY_TARGET =
  (import.meta.env.VITE_MA_API_PROXY_TARGET ?? "").trim() || "127.0.0.1:8003";

function getUploadErrorPayload(err: unknown) {
  const axiosErr = err as AxiosError<unknown>;

  return {
    hasResponse: Boolean(axiosErr?.response),
    status: axiosErr?.response?.status ?? null,
    rawBody:
      typeof axiosErr?.response?.data === "string"
        ? axiosErr.response.data
        : null,
    message: err instanceof Error ? err.message : "",
  };
}

export function shouldTreatUploadErrorAsDevBackendConnection(
  err: unknown,
  isLocalDev: boolean = DEV_LOCAL_AUTH_ENABLED,
) {
  if (!isLocalDev) {
    return false;
  }

  const { hasResponse, status, rawBody, message } = getUploadErrorPayload(err);
  const probe = `${rawBody ?? ""}\n${message}`.toLowerCase();

  if (!hasResponse) {
    return true;
  }

  if (status == null || ![500, 502, 503, 504].includes(status)) {
    return false;
  }

  return (
    probe.includes("econnrefused") ||
    probe.includes("connect ") ||
    probe.includes("socket hang up") ||
    probe.includes("etimedout") ||
    probe.includes("proxy error")
  );
}

export function buildUploadErrorMessage(
  err: unknown,
  {
    fallback,
    isLocalDev = DEV_LOCAL_AUTH_ENABLED,
    proxyTarget = DEV_MA_PROXY_TARGET,
  }: {
    fallback: string;
    isLocalDev?: boolean;
    proxyTarget?: string;
  },
) {
  if (shouldTreatUploadErrorAsDevBackendConnection(err, isLocalDev)) {
    return `개발 MA 백엔드(${proxyTarget})에 연결하지 못했습니다. deal-mgmt dev server가 실행 중인지 확인해 주세요.`;
  }

  return extractApiError(err, fallback);
}
