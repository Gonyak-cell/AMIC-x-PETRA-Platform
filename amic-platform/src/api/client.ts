import axios, { type AxiosInstance } from "axios";
import { emitForceLogout } from "@/lib/auth-events";

declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";
export const FDD_API_BASE_URL = "/api/fdd";
export const KIIS_API_BASE_URL = "/api/kiis";
export const IM_API_BASE_URL = "/api/im";
export const MA_API_BASE_URL = "/api/ma";
const FDD_REFRESH_URL =
  (import.meta.env.VITE_AUTH_REFRESH_URL ?? "").trim() ||
  `${FDD_API_BASE_URL}/auth/refresh`;
const MA_REFRESH_URL =
  (import.meta.env.VITE_MA_AUTH_REFRESH_URL ?? "").trim() ||
  `${MA_API_BASE_URL}/auth/refresh`;

const refreshPromises = new Map<string, Promise<boolean>>();
const apiClients = new Map<string, AxiosInstance>();

export async function refreshAuth(refreshUrl: string): Promise<boolean> {
  try {
    if (!refreshPromises.has(refreshUrl)) {
      const refreshPromise = axios
        .post<{ message: string }>(refreshUrl, {}, { withCredentials: true })
        .then(() => true)
        .finally(() => {
          refreshPromises.delete(refreshUrl);
        });
      refreshPromises.set(refreshUrl, refreshPromise);
    }
    return await refreshPromises.get(refreshUrl)!;
  } catch {
    return false;
  }
}

function resolveRefreshUrl(baseURL: string): string {
  if (DEV_LOCAL_AUTH_ENABLED && baseURL === MA_API_BASE_URL) {
    return MA_REFRESH_URL;
  }
  if (baseURL === MA_API_BASE_URL) {
    return MA_REFRESH_URL;
  }
  if (baseURL === FDD_API_BASE_URL) {
    return FDD_REFRESH_URL;
  }
  return `${baseURL}/auth/refresh`;
}

function applyAuthInterceptors(
  instance: AxiosInstance,
  refreshUrl: string,
): AxiosInstance {
  instance.interceptors.request.use((config) => {
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config;

      if (
        !error.response ||
        error.response.status !== 401 ||
        original._retry ||
        original.url === "/auth/login" ||
        original.url === "/auth/refresh" ||
        original.url === "/auth/me"
      ) {
        return Promise.reject(error);
      }

      if (DEV_LOCAL_AUTH_ENABLED && instance.defaults.baseURL === "/api/fdd") {
        return Promise.reject(error);
      }

      original._retry = true;

      try {
        const refreshed = await refreshAuth(refreshUrl);
        if (!refreshed) {
          emitForceLogout();
          return Promise.reject(error);
        }
        return instance(original);
      } catch {
        emitForceLogout();
        return Promise.reject(error);
      }
    },
  );

  return instance;
}

export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30_000,
    headers: { "Content-Type": "application/json; charset=utf-8" },
    withCredentials: true,
  });
  return applyAuthInterceptors(instance, resolveRefreshUrl(baseURL));
}

export function resolveAuthApiBasePath(pathname?: string): string {
  if (DEV_LOCAL_AUTH_ENABLED) {
    return MA_API_BASE_URL;
  }

  const normalizedPath = (pathname ?? "/").trim().toLowerCase();

  if (normalizedPath.startsWith("/fdd")) {
    return FDD_API_BASE_URL;
  }
  if (normalizedPath.startsWith("/kiis")) {
    return KIIS_API_BASE_URL;
  }
  if (normalizedPath.startsWith("/im")) {
    return IM_API_BASE_URL;
  }
  return MA_API_BASE_URL;
}

export function shouldSkipAuthBootstrapPath(pathname?: string): boolean {
  const normalizedPath = (pathname ?? "/").trim().toLowerCase();
  return normalizedPath === "/login" || normalizedPath === "/invite/accept";
}

export function getAuthApiForBase(baseURL: string): AxiosInstance {
  const existing = apiClients.get(baseURL);
  if (existing) {
    return existing;
  }

  const next = createApiClient(baseURL);
  apiClients.set(baseURL, next);
  return next;
}

export function getAuthApiForPath(pathname?: string): AxiosInstance {
  return getAuthApiForBase(resolveAuthApiBasePath(pathname));
}

export const authApi = getAuthApiForPath(
  typeof window !== "undefined" ? window.location.pathname : "/",
);

const api = getAuthApiForBase(FDD_API_BASE_URL);
export default api;
