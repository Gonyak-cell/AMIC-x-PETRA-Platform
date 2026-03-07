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

/**
 * 토큰 갱신을 시도한다. 성공 시 true, 실패 시 false.
 * axios 인터셉터와 native fetch 양쪽에서 호출 가능하도록 독립 함수로 분리.
 * 동시 호출 시 refreshPromise를 공유하여 1회만 실행된다.
 */
export async function refreshAuth(): Promise<boolean> {
  try {
    if (!refreshPromise) {
      refreshPromise = axios
        .post<{ message: string }>(
          REFRESH_URL,
          {},
          { withCredentials: true },
        )
        .then(() => true)
        .finally(() => {
          refreshPromise = null;
        });
    }
    return await refreshPromise;
  } catch {
    return false;
  }
}

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
        const refreshed = await refreshAuth();
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
    headers: { "Content-Type": "application/json" },
    withCredentials: true, // 쿠키 전송 활성화
  });
  return applyAuthInterceptors(instance);
}

// Default FDD client for backward compatibility
const api = createApiClient("/api/fdd");
export default api;
