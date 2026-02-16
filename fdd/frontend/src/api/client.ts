import axios from "axios";
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from "@/hooks/useAuth";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor: attach JWT ──

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: auto-refresh on 401 ──

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Skip refresh for login/refresh endpoints or already-retried requests
    if (
      !error.response ||
      error.response.status !== 401 ||
      original._retry ||
      original.url === "/auth/login" ||
      original.url === "/auth/refresh"
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
      // Deduplicate concurrent refresh calls
      if (!refreshPromise) {
        refreshPromise = axios
          .post<{ access_token: string; refresh_token: string }>(
            "/api/v1/auth/refresh",
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
      return api(original);
    } catch {
      clearTokens();
      window.location.href = "/login";
      return Promise.reject(error);
    }
  },
);

export default api;
