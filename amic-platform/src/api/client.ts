import axios, { type AxiosInstance } from "axios";
import { emitForceLogout } from "@/lib/auth-events";

// m6: _retry 커스텀 프로퍼티 타입 선언
declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

// M1: Token refresh 엔드포인트 환경변수화
const REFRESH_URL =
  import.meta.env.VITE_AUTH_REFRESH_URL || "/api/fdd/auth/refresh";

// ── Shared refresh promise to deduplicate concurrent 401 retries ──
let refreshPromise: Promise<boolean> | null = null;

function applyAuthInterceptors(instance: AxiosInstance): AxiosInstance {
  // Request: FormData 전송 시 Content-Type 제거 (브라우저가 multipart boundary 자동 설정)
  instance.interceptors.request.use((config) => {
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
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

      try {
        if (!refreshPromise) {
          // FDD is the central auth provider — all modules share this refresh endpoint
          // Refresh Token은 쿠키로 자동 전송됨
          refreshPromise = axios
            .post<{ message: string }>(
              REFRESH_URL,
              {}, // body 비우기 (쿠키로 전송됨)
              { withCredentials: true }, // 쿠키 전송 활성화
            )
            .then(() => {
              // 토큰 저장 불필요 (쿠키 자동 갱신)
              return true;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }

        await refreshPromise;
        return instance(original);
      } catch (refreshErr) {
        const is401 =
          axios.isAxiosError(refreshErr) && refreshErr.response?.status === 401;
        if (is401) {
          emitForceLogout();
        }
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
    headers: { "Content-Type": "application/json" },
    withCredentials: true, // 쿠키 전송 활성화
  });
  return applyAuthInterceptors(instance);
}

// Default FDD client for backward compatibility
const api = createApiClient("/api/fdd");
export default api;
