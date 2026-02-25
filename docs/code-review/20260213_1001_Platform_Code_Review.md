# Platform 공통 레이어 코드 리뷰

> **리뷰 일시**: 2026-02-13 09:16
> **검증 일시**: 2026-02-13 09:57
> **리뷰어**: Claude Code (Opus 4.6)
> **범위**: API client, Auth, Layout, UI components, Portal hooks/pages, Utilities
> **파일 수**: ~60개
> **방법론**: 3개 탐색 에이전트 분석 → 핵심 파일 직접 검증 → 오탐 제거 → 2차 소스코드 대조 검증

---

## 요약

| 심각도 | 건수 | 상태 |
|--------|------|------|
| Critical | 2 | 즉시 수정 필요 |
| Major | 13 | 조속히 수정 권장 |
| Minor | 10 | 개선 권장 |
| ~~오탐~~ | ~~3~~ | ~~제거~~ |
| **합계** | **25** | (원본 28건 중 3건 오탐 제거) |

> **검증 결과**: 원본 28건 중 25건 확인, 3건 오탐 제거, 3건 심각도 재분류(C2→M11, C3→M12, C5→m10), 누락 이슈 1건 추가(M13).

---

## 1. Critical 이슈 (2건)

### C1. logout 시 React Query 캐시 미삭제

- **파일**: `src/hooks/useAuth.ts:67-70`
- **심각도**: Critical
- **문제**: `logout()` 호출 시 토큰만 삭제하고 React Query 캐시를 클리어하지 않음. 로그아웃 후 다른 사용자가 로그인하면 이전 사용자의 캐시 데이터(딜, 문서, 기업 정보)가 staleTime(30초) 동안 노출됨.

```typescript
// 현재 코드
const logout = useCallback(() => {
  clearTokens();
  setAuthState({ user: null, isAuthenticated: false, isLoading: false });
}, [setAuthState]);
```

- **수정안**: `useAuth` 훅에서 `queryClient`에 접근하여 캐시를 클리어.

```diff
+ import { useQueryClient } from "@tanstack/react-query";

  export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
+   const queryClient = useQueryClient();

    const logout = useCallback(() => {
      clearTokens();
+     queryClient.clear();
      setAuthState({ user: null, isAuthenticated: false, isLoading: false });
-   }, [setAuthState]);
+   }, [setAuthState, queryClient]);
```

> **주의**: `main.tsx`에서 `AuthProvider`가 `QueryClientProvider` 내부에 있으므로 `useQueryClient()` 사용 가능. 현재 구조: `QueryClientProvider > BrowserRouter > AuthProvider`.

---

### C2. cn() 유틸리티가 tailwind-merge 미사용

- **파일**: `src/lib/cn.ts:5-7`
- **심각도**: Critical
- **문제**: `cn()`이 단순 `filter(Boolean).join(" ")`으로 구현되어 Tailwind 클래스 충돌을 해결하지 못함. 조건부 클래스에서 동일 유틸리티의 다른 값이 공존하면 CSS 생성 순서에 따라 어떤 값이 적용될지 비결정적.

```typescript
// 현재 코드
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
```

- **영향**: Input/Select 컴포넌트에서 error 상태일 때 `focus:ring-amic/20`과 `focus:ring-negative/20`이 동시에 적용되어 어느 쪽이 우선하는지 보장 불가 (M5, M6 연쇄 영향).
- **수정안**:

```diff
+ import { twMerge } from "tailwind-merge";
+ import { clsx, type ClassValue } from "clsx";

- export function cn(...classes: (string | boolean | undefined | null)[]): string {
-   return classes.filter(Boolean).join(" ");
- }
+ export function cn(...inputs: ClassValue[]): string {
+   return twMerge(clsx(inputs));
+ }
```

```bash
npm install tailwind-merge clsx
```

> **영향 범위**: 프로젝트 전체 (~60개 파일)에서 `cn()` 사용. `twMerge` 도입 시 기존 의도치 않은 클래스 중복이 해결되므로 UI 변경 사항 확인 필요.

---

## 2. Major 이슈 (13건)

### M1. Token refresh 엔드포인트 FDD 하드코딩

- **파일**: `src/api/client.ts:49-52`
- **심각도**: Major
- **문제**: 토큰 리프레시가 항상 `/api/fdd/auth/refresh`로 전송됨. FDD 백엔드가 다운되면 KIIS, IM 모듈도 인증 갱신 불가.

```typescript
// line 49-52
refreshPromise = axios
  .post<{ access_token: string; refresh_token: string }>(
    "/api/fdd/auth/refresh",  // ← 하드코딩
    { refresh_token: refresh },
  )
```

- **수정안**: 현재 "FDD = central auth provider" 아키텍처 결정이 코드 주석에만 존재. 이를 문서화하거나, 리프레시 엔드포인트를 환경변수로 설정.

```diff
+ // vite-env.d.ts
+ interface ImportMetaEnv {
+   readonly VITE_AUTH_REFRESH_URL: string;
+ }

  // client.ts
+ const REFRESH_URL = import.meta.env.VITE_AUTH_REFRESH_URL || "/api/fdd/auth/refresh";

  refreshPromise = axios
    .post<{ access_token: string; refresh_token: string }>(
-     "/api/fdd/auth/refresh",
+     REFRESH_URL,
      { refresh_token: refresh },
    )
```

---

### M2. useGlobalSearch IM fallback이 전체 문서 로드

- **파일**: `src/hooks/useGlobalSearch.ts:97-106`
- **심각도**: Major
- **문제**: IM 검색 API가 `search` 파라미터를 지원하지 않을 경우, catch 블록에서 **전체 문서**를 페이지네이션 없이 로드한 후 클라이언트 사이드 필터링. 문서가 10,000건 이상이면 메모리 폭증 및 UI 프리즈.

```typescript
// line 97-106
catch {
  const { data } = await imApi.get<{ items: Document[] }>("/documents");
  const q = debouncedQuery.toLowerCase();
  const filtered = data.items.filter(
    (d) =>
      d.company_name.toLowerCase().includes(q) ||
      (d.project_name?.toLowerCase().includes(q) ?? false),
  );
  return normalizeDocuments(filtered);
}
```

- **수정안**: fallback에 페이지 크기 제한 추가.

```diff
  catch {
-   const { data } = await imApi.get<{ items: Document[] }>("/documents");
+   const { data } = await imApi.get<{ items: Document[] }>("/documents", {
+     params: { limit: 200 },
+   });
    const q = debouncedQuery.toLowerCase();
    const filtered = data.items.filter(/* ... */);
    return normalizeDocuments(filtered);
  }
```

---

### M3. AuthProvider에서 401 vs 5xx 에러 미구분

- **파일**: `src/components/auth/AuthProvider.tsx:42-43,54-55`
- **심각도**: Major
- **문제**: `/auth/me` 응답의 catch 블록이 모든 에러를 동일하게 처리. 백엔드 일시 장애(500, 503)에도 토큰을 삭제하고 로그인 페이지로 이동시킴.

```typescript
// line 42-43 (토큰 없을 때)
.catch(() => {
  setState({ user: null, isAuthenticated: false, isLoading: false });
});

// line 54-55 (토큰 있을 때)
.catch(() => {
  clearTokens();  // ← 500 에러에도 토큰 삭제
  setState({ user: null, isAuthenticated: false, isLoading: false });
});
```

- **수정안**:

```diff
+ import axios from "axios";

  // 토큰 있을 때
  api.get<AuthUser>("/auth/me")
    .then(({ data }) => { /* ... */ })
-   .catch(() => {
-     clearTokens();
-     setState({ user: null, isAuthenticated: false, isLoading: false });
-   });
+   .catch((err) => {
+     if (axios.isAxiosError(err) && err.response?.status === 401) {
+       clearTokens();
+       setState({ user: null, isAuthenticated: false, isLoading: false });
+     } else {
+       // 서버 에러 — 토큰 유지, 에러 상태 표시
+       setState({ user: null, isAuthenticated: false, isLoading: false });
+     }
+   });
```

---

### M4. useNotifications endpointAvailableRef가 비반응적

- **파일**: `src/hooks/useNotifications.ts:8,59`
- **심각도**: Major
- **문제**: `endpointAvailableRef`는 `useRef`로 선언되어 값 변경 시 리렌더를 트리거하지 않음. 반환값 `endpointAvailable: endpointAvailableRef.current`는 호출 시점의 스냅샷이므로, 엔드포인트가 복구되어도 UI가 갱신되지 않음.

```typescript
// line 8
const endpointAvailableRef = useRef(true);

// line 59
return { ..., endpointAvailable: endpointAvailableRef.current };
```

- **수정안**: `useState`로 변경.

```diff
- const endpointAvailableRef = useRef(true);
+ const [endpointAvailable, setEndpointAvailable] = useState(true);

  // queryFn 내부
  try {
    const { data } = await api.get<NotificationItem[]>("/notifications");
-   endpointAvailableRef.current = true;
+   setEndpointAvailable(true);
    return data;
  } catch (error: unknown) {
    // ...
    if (status === 404 || status === 405) {
-     endpointAvailableRef.current = false;
+     setEndpointAvailable(false);
    }
    return [];
  }

  return {
    ...,
-   endpointAvailable: endpointAvailableRef.current,
+   endpointAvailable,
  };
```

---

### M5. Input 컴포넌트 focus ring 클래스 충돌

- **파일**: `src/components/ui/Input.tsx:36-38`
- **심각도**: Major
- **문제**: `cn()`이 `twMerge`를 사용하지 않으므로 (C2 참조), error 상태에서 `focus:ring-amic/20`과 `focus:ring-negative/20`이 모두 적용됨. CSS 생성 순서에 따라 어느 쪽이 우선할지 비결정적.

```typescript
// line 33-39
className={cn(
  "...",
  "focus:outline-none focus:ring-2 focus:ring-amic/20 focus:border-amic", // 항상 적용
  error
    ? "border-negative focus:ring-negative/20 focus:border-negative"  // 충돌!
    : "border-gray-border hover:border-amic-400",
  className
)}
```

- **수정안**: C2(twMerge 도입) 적용 시 자동 해결. twMerge 도입 전 임시 수정:

```diff
  className={cn(
    "w-full px-3 py-2 text-sm rounded-corporate border transition-colors",
    "bg-white text-text-body placeholder:text-text-secondary",
-   "focus:outline-none focus:ring-2 focus:ring-amic/20 focus:border-amic",
+   "focus:outline-none focus:ring-2",
    error
-     ? "border-negative focus:ring-negative/20 focus:border-negative"
-     : "border-gray-border hover:border-amic-400",
+     ? "border-negative focus:ring-negative/20 focus:border-negative"
+     : "border-gray-border hover:border-amic-400 focus:ring-amic/20 focus:border-amic",
    className
  )}
```

---

### M6. Select 컴포넌트 focus ring 클래스 충돌

- **파일**: `src/components/ui/Select.tsx:48-50`
- **심각도**: Major
- **문제**: Input(M5)과 동일한 패턴의 focus ring 충돌.

```typescript
// line 45-51
className={cn(
  "...",
  "focus:outline-none focus:ring-2 focus:ring-amic/20 focus:border-amic",
  error
    ? "border-negative focus:ring-negative/20 focus:border-negative"
    : "border-gray-border hover:border-amic-400",
  className
)}
```

- **수정안**: M5와 동일 패턴 적용. C2(twMerge 도입) 시 자동 해결.

---

### M7. ProtectedRoute가 인증만 확인, 권한 미확인

- **파일**: `src/components/auth/ProtectedRoute.tsx:10`
- **심각도**: Major
- **문제**: `isAuthenticated`만 체크. VIEWER 역할 사용자가 `/admin` URL을 직접 입력하면 접근 가능.

```typescript
// line 10
const { isAuthenticated, isLoading } = useAuth();

// line 21-23
if (!isAuthenticated) {
  return <Navigate to="/login" replace state={{ from: location }} />;
}
```

- **수정안**: `requiredPermission` prop 추가.

```diff
+ import type { Permission } from "@/types/auth";

  export default function ProtectedRoute({
    children,
+   requiredPermission,
  }: {
    children: React.ReactNode;
+   requiredPermission?: Permission;
  }) {
-   const { isAuthenticated, isLoading } = useAuth();
+   const { isAuthenticated, isLoading, hasPermission } = useAuth();
    const location = useLocation();

    if (isLoading) { /* ... */ }
    if (!isAuthenticated) {
      return <Navigate to="/login" replace state={{ from: location }} />;
    }
+   if (requiredPermission && !hasPermission(requiredPermission)) {
+     return <Navigate to="/" replace />;
+   }

    return <>{children}</>;
  }
```

---

### M8. useNotifications 에러 타입 체크에 `as` 단언 사용

- **파일**: `src/hooks/useNotifications.ts:17-21`
- **심각도**: Major
- **문제**: 에러 객체를 `as` 단언으로 캐스팅하여 타입 안전성 위반.

```typescript
// line 17-21
const status =
  error && typeof error === "object" && "response" in error
    ? (error as { response?: { status?: number } }).response?.status
    : undefined;
```

- **수정안**:

```diff
+ import axios from "axios";

  } catch (error: unknown) {
-   const status =
-     error && typeof error === "object" && "response" in error
-       ? (error as { response?: { status?: number } }).response?.status
-       : undefined;
+   const status = axios.isAxiosError(error) ? error.response?.status : undefined;
```

---

### M9. window.location.href 하드코딩으로 React Router 미연동

- **파일**: `src/api/client.ts:43,69`
- **심각도**: Major
- **문제**: 401 실패 시 `window.location.href = "/login"`으로 풀 페이지 리로드 발생. React Router의 `navigate()` 대신 브라우저 네비게이션 사용으로 앱 상태 초기화.

```typescript
// line 43
window.location.href = "/login";

// line 69
window.location.href = "/login";
```

- **수정안**: 현재 구조에서는 interceptor가 React 컴포넌트 외부에 있어 `useNavigate()` 사용 불가. 이벤트 기반 접근 권장.

```diff
+ // src/lib/auth-events.ts
+ export const AUTH_LOGOUT_EVENT = "auth:force-logout";
+ export function emitForceLogout() {
+   window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT));
+ }

  // client.ts
+ import { emitForceLogout } from "@/lib/auth-events";

  if (!refresh) {
    clearTokens();
-   window.location.href = "/login";
+   emitForceLogout();
    return Promise.reject(error);
  }

  // AuthProvider.tsx — 이벤트 리스너 추가
+ useEffect(() => {
+   const handler = () => {
+     clearTokens();
+     setState({ user: null, isAuthenticated: false, isLoading: false });
+   };
+   window.addEventListener(AUTH_LOGOUT_EVENT, handler);
+   return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handler);
+ }, []);
```

---

### M10. QueryClient에 전역 onError 핸들러 없음

- **파일**: `src/main.tsx:15-18`
- **심각도**: Major
- **문제**: React Query 쿼리/뮤테이션 실패 시 사용자에게 피드백이 없음. 네트워크 에러, 서버 에러 등이 조용히 무시됨.

```typescript
// line 15-18
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});
```

- **수정안**: TanStack Query v5에서는 `QueryCache`/`MutationCache`의 `onError`를 사용해야 전역 핸들링 가능. `defaultOptions.mutations.onError`만으로는 쿼리 에러가 누락됨.

```diff
+ import { QueryCache, MutationCache } from "@tanstack/react-query";
+ import { toast } from "sonner";

+ function handleGlobalError(error: Error) {
+   const message = error.message || "요청 처리 중 오류가 발생했습니다";
+   toast.error(message);
+ }

  const queryClient = new QueryClient({
+   queryCache: new QueryCache({
+     onError: handleGlobalError,
+   }),
+   mutationCache: new MutationCache({
+     onError: handleGlobalError,
+   }),
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1 },
    },
  });
```

> **[검증 보완]** 원본 수정안은 `mutations.onError`만 추가했으나, 쿼리 에러가 더 빈번하므로 `QueryCache.onError`도 필요. TanStack Query v5에서는 `defaultOptions`의 `onError`가 제거되었으므로 `QueryCache`/`MutationCache` 생성자를 사용해야 함.

---

### M11. useHealthCheck가 raw axios 사용으로 API 팩토리 우회

> **[검증] 원본 ID: C2 — 재분류: Critical → Major** (헬스체크는 인증 불필요 엔드포인트이므로 일관성 문제이지 보안 문제 아님)

- **파일**: `src/hooks/useHealthCheck.ts:4,20`
- **심각도**: Major
- **문제**: `import axios from "axios"`로 직접 axios를 사용하여 `/api/${service}/health` 호출. `createApiClient` 팩토리의 인터셉터(에러 핸들링, 로깅 등)가 우회됨.

```typescript
// 현재 코드 (line 4, 20)
import axios from "axios";
// ...
const { status } = await axios.get(`/api/${service}/health`, { timeout: 5000 });
```

- **수정안**: 각 모듈 API 클라이언트를 사용하도록 변경.

```diff
- import axios from "axios";
+ import api from "@/api/client";
+ import { kiisApi } from "@/api/kiisClient";
+ import { imApi } from "@/api/imClient";

+ const SERVICE_CLIENTS = {
+   fdd: api,
+   kiis: kiisApi,
+   im: imApi,
+ } as const;

  async function checkService(
    service: (typeof SERVICES)[number],
  ): Promise<ServiceStatus> {
    try {
-     const { status } = await axios.get(`/api/${service}/health`, {
-       timeout: 5000,
-     });
+     const { status } = await SERVICE_CLIENTS[service].get("/health", {
+       timeout: 5000,
+     });
      return status === 200 ? "healthy" : "degraded";
    } catch {
      return "down";
    }
  }
```

> **참고**: 헬스체크는 인증 불필요 엔드포인트이므로 raw axios도 기능적으로 동작하지만, 인터셉터 일관성과 에러 처리 통일을 위해 API 클라이언트 사용 권장.

---

### M12. AuthProvider useEffect에 AbortController 클린업 없음

> **[검증] 원본 ID: C3 — 재분류: Critical → Major** (React 19는 unmount 후 setState 경고를 제거. 메모리 누수일 뿐 크래시 아님)

- **파일**: `src/components/auth/AuthProvider.tsx:29-58`
- **심각도**: Major
- **문제**: 마운트 시 `/auth/me` API 호출의 클린업이 없음. React 19 StrictMode에서 이중 마운트 시 첫 번째 요청의 응답이 불필요한 setState를 호출할 수 있음 (크래시는 아니나 불필요한 네트워크 요청 발생).

```typescript
// 현재 코드 (line 29-58)
useEffect(() => {
  const token = getAccessToken();
  if (!token) {
    api.get<AuthUser>("/auth/me")
      .then(({ data }) => {
        setState({ ... }); // 이중 마운트 시 불필요한 호출
      })
      .catch(() => {
        setState({ ... });
      });
    return; // 클린업 없음
  }
  // ...
}, []);
```

- **수정안**:

```diff
  useEffect(() => {
+   const controller = new AbortController();
+   let cancelled = false;
    const token = getAccessToken();

    const fetchMe = () => {
-     api.get<AuthUser>("/auth/me")
+     api.get<AuthUser>("/auth/me", { signal: controller.signal })
        .then(({ data }) => {
+         if (cancelled) return;
          setState({ user: data, isAuthenticated: true, isLoading: false });
        })
        .catch(() => {
+         if (cancelled) return;
          if (token) clearTokens();
          setState({ user: null, isAuthenticated: false, isLoading: false });
        });
    };

    fetchMe();
+
+   return () => {
+     cancelled = true;
+     controller.abort();
+   };
  }, []);
```

---

### M13. client.ts ↔ useAuth.ts 순환 의존성

> **[검증] 신규 — 원본 리뷰에서 누락된 이슈**

- **파일**: `src/api/client.ts:1-7`, `src/hooks/useAuth.ts:5`
- **심각도**: Major
- **문제**: `client.ts`가 `useAuth.ts`에서 토큰 함수(`getAccessToken`, `getRefreshToken`, `setTokens`, `clearTokens`)를 import하고, `useAuth.ts`가 `client.ts`에서 `api`를 import. ES Module 순환 참조가 발생. 현재는 Vite의 모듈 해석 순서에 의존하여 동작하지만, 테스트 환경이나 번들러 변경 시 문제 발생 가능.

```
client.ts → import { getAccessToken, ... } from "@/hooks/useAuth"
useAuth.ts → import api from "@/api/client"
```

- **수정안**: 토큰 관련 함수를 별도 모듈로 분리.

```diff
+ // src/lib/token-storage.ts (신규 파일)
+ const ACCESS_TOKEN_KEY = "autofdd_access_token";
+ const REFRESH_TOKEN_KEY = "autofdd_refresh_token";
+
+ export function getAccessToken(): string | null { ... }
+ export function getRefreshToken(): string | null { ... }
+ export function setTokens(access: string, refresh: string): void { ... }
+ export function clearTokens(): void { ... }

  // client.ts
- import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/hooks/useAuth";
+ import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/token-storage";

  // useAuth.ts
+ import { getAccessToken, setTokens, clearTokens } from "@/lib/token-storage";
- const ACCESS_TOKEN_KEY = "autofdd_access_token";
- const REFRESH_TOKEN_KEY = "autofdd_refresh_token";
  // (토큰 함수 정의 제거, import로 대체)
```

---

## 3. Minor 이슈 (10건)

### m1. 토큰 키 `autofdd_*` 하드코딩

- **파일**: `src/hooks/useAuth.ts:14-15`
- **심각도**: Minor
- **문제**: `ACCESS_TOKEN_KEY = "autofdd_access_token"` — "autofdd" 접두사가 FDD 단일 모듈 시절의 잔재. 플랫폼 통합 후에도 그대로 사용 중. 기능 문제는 없으나, 새 개발자에게 혼동 유발.
- **수정안**: 키 이름 변경은 기존 사용자 세션이 끊기므로, 마이그레이션 코드가 필요. 현재는 코드 주석으로 문서화 권장.

### m2. ProtectedRoute Skeleton에 aria-label 없음

- **파일**: `src/components/auth/ProtectedRoute.tsx:16`
- **심각도**: Minor
- **문제**: 로딩 중 Skeleton에 `role="status"` 또는 `aria-label`이 없어 스크린리더 사용자가 인증 확인 중임을 알 수 없음.
- **수정안**: `<div role="status" aria-label="인증 확인 중...">` 추가.

### m3. API 응답 런타임 검증 없이 타입 단언

- **파일**: `src/hooks/useAnalytics.ts:145,164`
- **심각도**: Minor
- **문제**: `api.get<Deal[]>("/deals")`의 응답을 런타임 검증 없이 `Deal[]`로 신뢰. 백엔드 스키마 변경 시 런타임 크래시 가능.
- **수정안**: zod 스키마 도입 또는 타입 가드 추가 (장기적 개선).

### m4. DataTable 로딩 시 고정 5행 스켈레톤

- **파일**: `src/components/ui/DataTable.tsx:126`
- **심각도**: Minor
- **문제**: `[...Array(5)]`로 항상 5행 표시. 실제 데이터가 2행 또는 20행이면 레이아웃 시프트 발생.
- **수정안**: `skeletonRows` prop 추가 또는 이전 데이터 길이 기반 동적 계산.

### m5. login 함수가 useMutation 미사용

- **파일**: `src/hooks/useAuth.ts:47-65`
- **심각도**: Minor
- **문제**: `login()`이 일반 async 함수로 구현되어 `isPending`, `isError` 등의 상태를 반환하지 않음. 호출 컴포넌트에서 직접 로딩 상태 관리 필요.
- **수정안**: `useMutation` 기반으로 리팩토링 (기존 호출부 변경 필요).

### m6. `original._retry` 타입 미선언

- **파일**: `src/api/client.ts:31`
- **심각도**: Minor
- **문제**: `original._retry`는 AxiosRequestConfig에 없는 커스텀 프로퍼티. TypeScript strict 모드에서 에러 가능.
- **수정안**:

```typescript
declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}
```

### m7. DataTable Column.key가 `string` 타입

- **파일**: `src/components/ui/DataTable.tsx:7`
- **심각도**: Minor
- **문제**: `key: string`이므로 오타나 존재하지 않는 프로퍼티명 사용 시 컴파일 에러 없음.
- **수정안**: `key: Extract<keyof T, string>` 변경 (단, 커스텀 키 사용 시 호환성 이슈 가능).

### m8. getItem의 `JSON.parse(raw) as T` 런타임 검증 없음

- **파일**: `src/lib/storage.ts:7`
- **심각도**: Minor
- **문제**: localStorage 데이터가 변조되었을 때 잘못된 타입의 객체가 반환됨.
- **수정안**: 장기적으로 zod 스키마 검증 도입. 현재는 try-catch (이미 구현됨)로 충분.

### m9. Modal dialog.showModal() 브라우저 지원

- **파일**: `src/components/ui/Modal.tsx:46`
- **심각도**: Minor
- **문제**: `<dialog>` 요소의 `showModal()` 메서드가 IE11, 일부 모바일 브라우저에서 미지원.
- **수정안**: 대상 브라우저가 모던 브라우저만이면 수정 불필요. Polyfill 필요 시 `dialog-polyfill` 패키지 사용.

### m10. storage.ts setItem에 try-catch 없음

> **[검증] 원본 ID: C5 — 재분류: Critical → Minor** (QuotaExceededError는 현대 브라우저 5-10MB 쿼터 기준 발생 확률 극히 낮음. 방어적 코딩 개선)

- **파일**: `src/lib/storage.ts:13-14`
- **심각도**: Minor
- **문제**: `localStorage.setItem()`은 쿼터 초과 시 `QuotaExceededError`를 throw. 현재 코드에 에러 핸들링이 없음. 이 앱에서 저장하는 데이터(`favorites`, `recent_searches`)는 수 KB 수준이므로 현실적 발생 확률은 극히 낮으나, 방어적 코딩이 바람직.

```typescript
// 현재 코드
export function setItem<T>(key: string, value: T): void {
  localStorage.setItem(PREFIX + key, JSON.stringify(value));
}
```

- **수정안**:

```diff
  export function setItem<T>(key: string, value: T): void {
+   try {
      localStorage.setItem(PREFIX + key, JSON.stringify(value));
+   } catch {
+     // QuotaExceededError — 조용히 무시 (데이터 미저장, 기능은 계속)
+     console.warn(`[storage] Failed to save key "${key}" — quota exceeded`);
+   }
  }
```

---

## ~~4. 검증 시 제거된 오탐 (3건)~~

> 원본 리뷰의 m5, m10, m13은 실제 코드 대조 결과 오탐으로 확인되어 제거됨.

### ~~원본 m5. HealthIndicator에서 undefined 상태 접근 가능~~ — 오탐

- ~~**파일**: `src/components/layout/HealthIndicator.tsx`~~
- **제거 사유**: `health` 객체는 `useHealthCheck.ts:39-43`에서 `{ fdd, kiis, im }` 세 키를 명시적으로 초기화하는 로컬 구성 객체. TypeScript `HealthStatus` 타입이 세 키 모두 `ServiceStatus`로 보장하므로 `health[key]`가 `undefined`가 되는 경우는 사실상 불가능.

### ~~원본 m10. useGlobalSearch 디바운스 setState 경고~~ — 오분석

- ~~**파일**: `src/hooks/useGlobalSearch.ts:58-61`~~
- **제거 사유**: `useEffect` cleanup에서 `clearTimeout(timer)`가 호출되므로, 언마운트 시 예약된 `setDebouncedQuery`는 정상적으로 **취소**됨. "해제 시 이미 스케줄된 호출이 실행될 수 있음"이라는 원본 분석은 잘못됨.

### ~~원본 m13. Modal 포커스 가능 요소 없을 때 fallback 없음~~ — 구조 오인

- ~~**파일**: `src/components/ui/Modal.tsx:50-53`~~
- **제거 사유**: `contentRef`는 전체 패널(`bg-white rounded-corporate` div)을 감싸며, 닫기 버튼은 헤더 내부 = `contentRef` **내부**에 위치. `querySelector(FOCUSABLE_SELECTOR)`가 항상 닫기 버튼을 찾으므로 fallback 부재가 아님.

---

## 5. 긍정적 패턴

1. **API 팩토리 패턴**: `createApiClient(baseURL)`로 3개 모듈 클라이언트를 일관되게 생성. 인터셉터 공유 구조 우수.
2. **토큰 리프레시 중복 방지**: `refreshPromise` 패턴으로 동시 401 요청의 토큰 리프레시를 단일 요청으로 통합 (client.ts:10,48,60).
3. **접근성 기반 설계**: Modal의 `aria-labelledby`, Input/Select의 `aria-invalid`, `aria-describedby`, DataTable의 키보드 네비게이션 등 WCAG 기본 준수.
4. **Sentry 통합**: `SentryErrorBoundary`, `initSentry()`, HealthCheck 실패 시 `Sentry.captureMessage()` 등 에러 모니터링 체계.
5. **MSW 기반 테스트**: `enableMocking()` → 개발/테스트 환경에서 API 모킹 자동 활성화.
6. **Auth 상태 관리**: AuthContext + AuthProvider로 인증 상태를 React 트리 최상위에서 관리. `useAuth()` 훅으로 일관된 접근.

---

## 6. 수정 우선순위 권장

### P0: 즉시 수정 (보안/안정성)
1. **C2** — `cn()`에 `tailwind-merge` 도입 → M5, M6 자동 해결
2. **C1** — logout 시 `queryClient.clear()` 추가
3. **M13** — 순환 의존성 해소 (`token-storage.ts` 분리)

### P1: 1주 내 수정
4. **M3** — AuthProvider 401 vs 5xx 구분
5. **M7** — ProtectedRoute 권한 체크 추가
6. **M8** — useNotifications axios.isAxiosError() 사용
7. **M4** — useNotifications useState로 변경
8. **M12** — AuthProvider AbortController 클린업

### P2: 2주 내 수정
9. **M1** — Token refresh 엔드포인트 환경변수화
10. **M2** — useGlobalSearch IM fallback 제한
11. **M9** — window.location.href 이벤트 기반 전환
12. **M10** — QueryClient 전역 에러 핸들러
13. **M11** — useHealthCheck API 클라이언트 사용

### P3: 백로그
14. m1~m10 — 리팩토링 시 함께 처리

---

## 7. 검증 이력

| 항목 | 원본 (09:16) | 검증 후 (09:57) |
|------|-------------|-----------------|
| Critical | 5건 | **2건** (C2,C3→Major, C5→Minor) |
| Major | 10건 | **13건** (+C2,C3,순환의존성) |
| Minor | 13건 | **10건** (−3 오탐, +C5) |
| 합계 | 28건 | **25건** (3 오탐 제거) |
| M10 수정안 | mutations.onError만 | **QueryCache+MutationCache** |
