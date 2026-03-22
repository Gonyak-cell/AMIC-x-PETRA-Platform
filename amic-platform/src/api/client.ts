import axios, { type AxiosInstance } from "axios";
import { emitForceLogout } from "@/lib/auth-events";

declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";
const FDD_REFRESH_URL =
  (import.meta.env.VITE_AUTH_REFRESH_URL ?? "").trim() ||
  "/api/fdd/auth/refresh";
const MA_REFRESH_URL =
  (import.meta.env.VITE_MA_AUTH_REFRESH_URL ?? "").trim() ||
  "/api/ma/auth/refresh";

const refreshPromises = new Map<string, Promise<boolean>>();

export async function refreshAuth(refreshUrl: string): Promise<boolean> {
  try {
    if (!refreshPromises.has(refreshUrl)) {
      const refreshPromise = axios
        .post<{ message: string }>(
          refreshUrl,
          {},
          { withCredentials: true },
        )
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
  if (DEV_LOCAL_AUTH_ENABLED && baseURL === "/api/ma") {
    return MA_REFRESH_URL;
  }
  return FDD_REFRESH_URL;
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

export const authApi = createApiClient(
  DEV_LOCAL_AUTH_ENABLED ? "/api/ma" : "/api/fdd",
);

const api = createApiClient("/api/fdd");
export default api;
