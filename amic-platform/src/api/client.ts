import axios, { type AxiosInstance } from "axios";
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from "@/hooks/useAuth";

// ── Shared refresh promise to deduplicate concurrent 401 retries ──
let refreshPromise: Promise<string> | null = null;

function applyAuthInterceptors(instance: AxiosInstance): AxiosInstance {
  // Request: attach JWT
  instance.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Response: auto-refresh on 401
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

      original._retry = true;
      const refresh = getRefreshToken();
      if (!refresh) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post<{ access_token: string; refresh_token: string }>(
              "/api/fdd/auth/refresh",
              { refresh_token: refresh },
            )
            .then(({ data }) => {
              setTokens(data.access_token, data.refresh_token);
              return data.access_token;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }

        const newToken = await refreshPromise;
        original.headers.Authorization = `Bearer ${newToken}`;
        return instance(original);
      } catch {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }
    },
  );

  return instance;
}

export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    headers: { "Content-Type": "application/json" },
  });
  return applyAuthInterceptors(instance);
}

// Default FDD client for backward compatibility
const api = createApiClient("/api/fdd");
export default api;
