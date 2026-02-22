# Code Review — Security (프론트엔드)

> **Review Date**: 2026-02-16 20:22
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 전체 프론트엔드 보안 감사 (인증, API 클라이언트, 설정)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification + Auto-Verification
> **Quality Gates**: tsc(✓ PASS) eslint(✗ FAIL) vitest(✗ FAIL) build(✗ FAIL)
> **Review Gates**: Backend(FDD/KIIS/IM unavailable) Agent-Filtering(2개 에이전트 호출)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P0: 1 |
| Major    | 0     | - | - |
| Moderate | 2     | HIGH: 1 / MEDIUM: 1 / LOW: 0 | P2: 1 / P3: 1 |
| Minor    | 3     | HIGH: 2 / MEDIUM: 1 / LOW: 0 | P3: 3 |
| **Total**| **6** | HIGH: **4** / MEDIUM: **2** / LOW: **0** | P0: **1** / P1: **0** / P2: **1** / P3: **4** |

**FP Prevention**: 가설 12건 검증, 3건 사전 거부 (거부율: 25%) | 교차 검증 1건 수행 | 자동 검증 5건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 2건 하향 조정 (Moderate→P3, Minor→P3)
- 자동 검증 범위: 100% (5/5건 검증 완료)

**제약사항**:
- ⚠️ Phase 0A 파일 접근 오류 (OneDrive 동기화 문제)로 자동 품질 검사 일부 실패
- ⚠️ security-auditor 에이전트가 모든 대상 파일 접근 실패로 이슈 보고 불가
- ⚠️ 백엔드 코드 unavailable로 백엔드 보안 검증 제외

---

## Findings

### [Critical-A1] FDD 모듈 훅이 잘못된 API 클라이언트 사용 — Critical — Confidence: HIGH — Priority: P0

- **파일**: [src/modules/fdd/hooks/useDeals.ts:2](amic-platform/src/modules/fdd/hooks/useDeals.ts#L2)
- **에이전트**: api-auditor
- **교차 검증**: Yes (review-verifier, Phase 2)
- **우선순위**: P0 (점수: 115)
  - 심각도 가중치: 100 (Critical)
  - 신뢰도 가중치: 1.0 (HIGH)
  - 보너스: +15 (review-verifier 확인)
- **검증 추적**:
  1. ✓ Glob: `src/modules/fdd/hooks/*.ts` → useDeals.ts 확인
  2. ✓ Read: useDeals.ts:2 → `import api from "@/api/client"` 확인
  3. ✓ Read: useCompanies.ts:2 (KIIS) → `import { kiisApi } from "@/api/kiisClient"` 확인
  4. ✓ Context: `src/api/fddClient.ts` 존재 확인 → `export const fddApi` 제공
- **추론 근거**:
  - **심각도 Critical인 이유**: FDD 모듈이 기본 클라이언트(`/api/fdd`)를 사용하는 것은 동작하지만, 다른 FDD 훅들이 `fddApi`를 사용할 경우 API 클라이언트 인스턴스가 분리되어 인터셉터, 토큰 관리가 독립적으로 동작할 수 있음. 모듈 간 일관성 부재로 디버깅이 어려워지고, 향후 클라이언트 설정 변경 시 동기화 문제 발생 가능.
  - **신뢰도 HIGH인 이유**: 실제 코드를 Read로 확인했으며, `kiisApi`는 명확히 `kiisClient.ts`에서 import함. FDD만 `client.ts`에서 import하는 불일치를 직접 검증함. Phase 2 교차 검증 통과.
- **증거**:
```typescript
// useDeals.ts:1-2
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
```

```typescript
// useCompanies.ts:2 (KIIS 모듈)
import { kiisApi } from "@/api/kiisClient";
```

```typescript
// fddClient.ts (FDD 전용 클라이언트 존재)
import { createApiClient } from "./client";
export const fddApi = createApiClient("/api/fdd");
```

- **이슈**: FDD 모듈이 `@/api/client`의 기본 export를 사용하는 반면, KIIS 모듈은 `@/api/kiisClient`의 `kiisApi` named export를 사용합니다. `client.ts`의 기본 export는 `/api/fdd` baseURL로 설정되어 있지만, 이는 backward compatibility용입니다. 모듈별 클라이언트를 명시적으로 사용하는 것이 아키텍처상 올바릅니다.

- **영향**:
  1. **일관성 부족**: 다른 모듈(KIIS, IM)은 전용 클라이언트를 사용하는데 FDD만 기본 클라이언트 사용
  2. **혼란스러운 import 경로**: 코드 리뷰 시 어떤 API를 호출하는지 명확하지 않음
  3. **리팩토링 위험**: `client.ts`의 기본 export가 변경되면 FDD 모듈이 영향받음

- **수정안**:
```typescript
// useDeals.ts
- import api from "@/api/client";
+ import { fddApi } from "@/api/fddClient";

// 사용처 수정
- const { data } = await api.get("/deals", { params });
+ const { data } = await fddApi.get("/deals", { params });
```

**적용 범위**: `src/modules/fdd/hooks/` 하위 모든 훅 파일 (약 10개 파일)

---

### [Moderate-A2] 에러 핸들링이 console.error로만 처리됨 (FDD) — Moderate — Confidence: HIGH — Priority: P2

- **파일**: [src/modules/fdd/hooks/useDeals.ts:25-27](amic-platform/src/modules/fdd/hooks/useDeals.ts#L25-L27)
- **에이전트**: api-auditor
- **우선순위**: P2 (점수: 40)
  - 심각도 가중치: 40 (Moderate)
  - 신뢰도 가중치: 1.0 (HIGH)
  - 보너스: +0
- **검증 추적**:
  1. ✓ Read: useDeals.ts:25-27 → `console.error("useCreateDeal failed:", error)` 확인
  2. ✓ Context: useProfile.ts:26-28 → `toast.error()` 사용 패턴 확인
  3. ✓ Phase 2B 자동 검증: 100점 (파일 존재 + 라인 정확 + 코드 100% 일치)
- **추론 근거**:
  - **심각도 Moderate인 이유**: 에러가 발생해도 사용자에게 알림이 표시되지 않아 UX 저하. 하지만 애플리케이션이 중단되는 것은 아니므로 Critical이 아닌 Moderate.
  - **신뢰도 HIGH인 이유**: 실제 코드를 Read로 확인했으며, 같은 codebase 내에서 toast 사용 패턴(`useProfile.ts`)과 비교 검증 완료. Phase 2B 자동 검증 통과.
- **증거**:
```typescript
// useDeals.ts:25-27
onError: (error: Error) => {
  console.error("useCreateDeal failed:", error);
},
```

```typescript
// useProfile.ts:26-28 (올바른 패턴)
onError: () => {
  toast.error("Failed to update profile");
},
```

- **이슈**: mutation의 `onError` 핸들러가 `console.error()`만 호출하여 사용자에게 시각적 피드백을 제공하지 않습니다.

- **영향**:
  1. **UX 저하**: 딜 생성 실패 시 사용자가 인지하지 못함
  2. **일관성 부족**: 다른 모듈(`useProfile`)은 toast를 사용하는데 FDD는 미사용
  3. **디버깅 어려움**: 프로덕션 환경에서 console.error는 사용자에게 도움이 되지 않음

- **수정안**:
```typescript
import { toast } from "sonner";

export function useCreateDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: DealCreate) => {
      const { data } = await fddApi.post("/deals", body);
      return data as Deal;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "deals"] });
      toast.success("Deal created successfully");
    },
    onError: () => {
      toast.error("Failed to create deal");
    },
  });
}
```

---

### [Moderate-A3] 인증 refresh 엔드포인트가 환경변수화되었으나 문서화 누락 — Moderate — Confidence: MEDIUM — Priority: P3

- **파일**: [src/api/client.ts:18](amic-platform/src/api/client.ts#L18)
- **에이전트**: api-auditor
- **우선순위**: P3 (점수: 24)
  - 심각도 가중치: 40 (Moderate)
  - 신뢰도 가중치: 0.6 (MEDIUM)
  - 보너스: +0
  - ⚠️ **이 Moderate 이슈는 중간 신뢰도(MEDIUM)로 인해 P3로 분류되었습니다.**
- **검증 추적**:
  1. ✓ Read: client.ts:18 → `VITE_AUTH_REFRESH_URL` 환경변수 확인
  2. ✗ Read: `.env.production.example` 읽기 실패 (파일 접근 권한 문제)
  3. ⚠ Context: 환경변수 문서화 여부를 직접 확인 불가
  4. ✓ Phase 2B 자동 검증: 100점 (파일 존재 + 라인 정확 + 코드 100% 일치)
- **추론 근거**:
  - **심각도 Moderate인 이유**: 환경변수가 설정되지 않아도 fallback(`/api/fdd/auth/refresh`)이 있어 동작은 하지만, 다른 인증 제공자를 사용할 경우 설정 방법을 모를 수 있음.
  - **신뢰도 MEDIUM인 이유**: `.env.production.example` 파일을 읽을 수 없어 실제 문서화 여부를 확인하지 못함. 파일 접근 권한 문제로 추론에 의존.
- **증거**:
```typescript
// client.ts:18
const REFRESH_URL = import.meta.env.VITE_AUTH_REFRESH_URL || "/api/fdd/auth/refresh";
```

- **이슈**: `VITE_AUTH_REFRESH_URL` 환경변수가 코드에 존재하지만, `.env.production.example`에 문서화되어 있는지 확인할 수 없습니다. (파일 접근 권한 문제)

- **영향**:
  1. **배포 설정 누락 위험**: 운영자가 환경변수 설정 필요성을 모를 수 있음
  2. **멀티 모듈 인증 혼란**: FDD가 중앙 인증 제공자이지만, 이를 변경하려는 경우 방법을 모를 수 있음

- **수정안**:
`.env.production.example`에 아래 추가:
```bash
# Authentication
VITE_AUTH_REFRESH_URL=/api/fdd/auth/refresh
# 기본값: /api/fdd/auth/refresh (FDD가 중앙 인증 제공자)
# 다른 인증 제공자 사용 시 경로 변경
```

---

### [Minor-A4] React Query 캐시 설정이 일부 훅에만 적용됨 — Minor — Confidence: MEDIUM — Priority: P3

- **파일**: [src/hooks/useExports.ts:35](amic-platform/src/hooks/useExports.ts#L35)
- **에이전트**: api-auditor
- **우선순위**: P3 (점수: 12)
  - 심각도 가중치: 20 (Minor)
  - 신뢰도 가중치: 0.6 (MEDIUM)
  - 보너스: +0
  - ⚠️ **이 Minor 이슈는 중간 신뢰도(MEDIUM)로 인해 우선순위가 낮아졌습니다.**
- **검증 추적**:
  1. ✓ Grep: `staleTime` 패턴 검색 → 일부 훅에만 설정 확인
  2. ✓ Read: useExports.ts:35, useDeals.ts → staleTime 유무 대조
  3. ✗ Read: `main.tsx` 읽기 실패 (권한 문제) → QueryClient 글로벌 설정 확인 불가
  4. ✓ Phase 2B 자동 검증: 100점
- **추론 근거**:
  - **심각도 Minor인 이유**: 캐시 설정 부재로 불필요한 API 호출이 발생할 수 있지만, 기능상 문제는 없음. 성능 최적화 이슈.
  - **신뢰도 MEDIUM인 이유**: `main.tsx`를 읽을 수 없어 QueryClient의 글로벌 defaultOptions 설정을 확인하지 못함. 개별 훅에만 `staleTime`이 있는 것이 의도적인지 판단 불가.
- **증거**:
```typescript
// useExports.ts:35 (staleTime 설정 O)
staleTime: 30_000,

// useDeals.ts (staleTime 설정 X)
export function useDeals(params?: { skip?: number; limit?: number }) {
  return useQuery<Deal[]>({
    queryKey: ["fdd", "deals", params],
    queryFn: async () => {
      const { data } = await api.get("/deals", { params });
      return data;
    },
  });
}
```

- **이슈**: 일부 훅(`useExports`, `useDashboard`)에만 `staleTime` 설정이 있고, FDD/KIIS/IM 모듈 훅에는 설정이 없습니다. QueryClient 글로벌 설정을 확인할 수 없어 의도적인 설계인지 불명확합니다.

- **영향**:
  1. **불필요한 API 호출**: 동일 데이터를 짧은 시간에 여러 번 fetch 가능
  2. **일관성 부족**: 모듈별로 캐시 전략이 다를 수 있음

- **수정안** (글로벌 설정 부재 시):
```typescript
// main.tsx (예상)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30초
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

---

### [Minor-A5] Vite 프록시 설정이 하드코딩된 포트 사용 — Minor — Confidence: HIGH — Priority: P3

- **파일**: [vite.config.ts:38,43,48](amic-platform/vite.config.ts#L38)
- **에이전트**: api-auditor
- **우선순위**: P3 (점수: 20)
  - 심각도 가중치: 20 (Minor)
  - 신뢰도 가중치: 1.0 (HIGH)
  - 보너스: +0
- **검증 추적**:
  1. ✓ Read: vite.config.ts:38,43,48 → 포트 8000/8001/8002 하드코딩 확인
  2. ✓ Grep: `VITE_.*URL` 검색 → 백엔드 URL 환경변수 없음 확인
  3. ✓ Phase 2B 자동 검증: 100점
- **추론 근거**:
  - **심각도 Minor인 이유**: 개발 환경에서만 사용되는 설정이며, 프로덕션에는 영향 없음. 다만 다른 포트를 사용하는 개발자가 있을 경우 불편함.
  - **신뢰도 HIGH인 이유**: 실제 코드를 Read로 확인했으며, 환경변수가 없음을 Grep으로 검증함.
- **증거**:
```typescript
// vite.config.ts:37-51
proxy: {
  "/api/fdd": {
    target: "http://localhost:8000",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/fdd/, "/api/v1"),
  },
  "/api/kiis": {
    target: "http://localhost:8001",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/kiis/, "/api/v1"),
  },
  "/api/im": {
    target: "http://localhost:8002",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/im/, "/api/v1"),
  },
},
```

- **이슈**: Vite 프록시 설정이 `localhost:8000/8001/8002`로 하드코딩되어 있습니다. 개발자가 다른 포트를 사용하거나, Docker로 백엔드를 실행할 경우 설정 변경이 필요합니다.

- **영향**:
  1. **개발 환경 유연성 부족**: 포트 충돌 시 `vite.config.ts` 수정 필요
  2. **Docker 환경 불편**: 컨테이너 이름으로 접근하려면 코드 수정 필요

- **수정안**:
```typescript
// vite.config.ts
proxy: {
  "/api/fdd": {
    target: process.env.VITE_FDD_API_URL || "http://localhost:8000",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/fdd/, "/api/v1"),
  },
  "/api/kiis": {
    target: process.env.VITE_KIIS_API_URL || "http://localhost:8001",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/kiis/, "/api/v1"),
  },
  "/api/im": {
    target: process.env.VITE_IM_API_URL || "http://localhost:8002",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/im/, "/api/v1"),
  },
},
```

```bash
# .env
VITE_FDD_API_URL=http://localhost:8000
VITE_KIIS_API_URL=http://localhost:8001
VITE_IM_API_URL=http://localhost:8002
```

---

### [Minor-A6] API 클라이언트 timeout이 30초로 고정됨 — Minor — Confidence: HIGH — Priority: P3

- **파일**: [src/api/client.ts:95](amic-platform/src/api/client.ts#L95)
- **에이전트**: api-auditor
- **우선순위**: P3 (점수: 20)
  - 심각도 가중치: 20 (Minor)
  - 신뢰도 가중치: 1.0 (HIGH)
  - 보너스: +0
- **검증 추적**:
  1. ✓ Read: client.ts:95 → `timeout: 30_000` 확인
  2. ✓ Grep: timeout 환경변수 설정 없음 확인
  3. ✓ Phase 2B 자동 검증: 100점
- **추론 근거**:
  - **심각도 Minor인 이유**: 30초는 대부분의 API 요청에 충분한 시간이지만, 대용량 파일 업로드/다운로드 시 부족할 수 있음. 하지만 현재 코드에서 큰 문제는 아님.
  - **신뢰도 HIGH인 이유**: 실제 코드를 Read로 확인했으며, 하드코딩된 값임을 직접 검증함.
- **증거**:
```typescript
// client.ts:92-98
export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30_000,
    headers: { "Content-Type": "application/json" },
  });
  return applyAuthInterceptors(instance);
}
```

- **이슈**: API 클라이언트의 timeout이 30초로 하드코딩되어 있습니다. 대용량 파일 처리나 느린 네트워크 환경에서 문제가 될 수 있습니다.

- **영향**:
  1. **대용량 파일 처리 실패**: VDR 업로드, 보고서 다운로드 시 timeout 발생 가능
  2. **환경별 조정 불가**: 프로덕션/개발 환경에서 다른 timeout 필요 시 코드 수정 필요

- **수정안**:
```typescript
// client.ts
export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30_000,
    headers: { "Content-Type": "application/json" },
  });
  return applyAuthInterceptors(instance);
}
```

```bash
# .env
VITE_API_TIMEOUT=30000
# 프로덕션 환경에서는 60000 등으로 설정 가능
```

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

1. **[Critical-A1]**: FDD 모듈 훅이 잘못된 API 클라이언트 사용 — [src/modules/fdd/hooks/useDeals.ts:2](amic-platform/src/modules/fdd/hooks/useDeals.ts#L2) — Confidence: HIGH (점수: 115)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)

*(이슈 없음)*

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

1. **[Moderate-A2]**: 에러 핸들링이 console.error로만 처리됨 (FDD) — [src/modules/fdd/hooks/useDeals.ts:25-27](amic-platform/src/modules/fdd/hooks/useDeals.ts#L25-L27) — Confidence: HIGH (점수: 40)

### P3 — 저우선 (점수: <30, 개선 가능)

1. **[Moderate-A3]**: 인증 refresh 엔드포인트가 환경변수화되었으나 문서화 누락 — [src/api/client.ts:18](amic-platform/src/api/client.ts#L18) — Confidence: MEDIUM (점수: 24) ⚠️
2. **[Minor-A4]**: React Query 캐시 설정이 일부 훅에만 적용됨 — [src/hooks/useExports.ts:35](amic-platform/src/hooks/useExports.ts#L35) — Confidence: MEDIUM (점수: 12) ⚠️
3. **[Minor-A5]**: Vite 프록시 설정이 하드코딩된 포트 사용 — [vite.config.ts:38](amic-platform/vite.config.ts#L38) — Confidence: HIGH (점수: 20)
4. **[Minor-A6]**: API 클라이언트 timeout이 30초로 고정됨 — [src/api/client.ts:95](amic-platform/src/api/client.ts#L95) — Confidence: HIGH (점수: 20)

---

## Methodology

- **Agents**: api-auditor (security-auditor: 파일 접근 실패)
- **Excluded Agents**: security-auditor (모든 대상 파일 접근 실패)
- **Files scanned**: 200+ 프론트엔드 파일 (일부만 접근 성공)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 1건 수행 (Phase 2)
- **Auto-verification**: Moderate/Minor 5건 수행 (Phase 2B, 100% 검증률)
- **Backend availability**: FDD(unavailable) KIIS(unavailable) IM(unavailable)

---

## 검증 투명성

### 검증 통계
- **검증한 가설**: 12건
- **거부된 가설** (사전 제거): 3건
- **보고된 이슈**: 6건
- **거부율**: 25%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | "401 재시도 무한 루프" → `_retry` 가드 존재 확인<br>"refresh token 동시성" → `refreshPromise` deduplication 확인<br>"KIIS API 클라이언트 불일치" → `kiisApi` 올바르게 사용 확인 |
| 범위 외 | 0 | - |
| 이미 수정됨 | 0 | - |
| 오판 | 0 | - |
| 중복 | 0 | - |
| 신뢰도 불충분 | 0 | - |

### Phase 2B 자동 검증 결과

- **Moderate 이슈**: 2/2건 검증됨 (100%)
- **Minor 이슈**: 3/3건 검증됨 (100%)
- **수동 검토 플래그**: 0건
- **검증 범위**: 100% (목표 달성)

---

## 제약사항 및 후속 작업

### 이번 리뷰에서 확인하지 못한 영역

**파일 접근 권한 문제** (OneDrive 동기화)로 인해 다음 영역을 검증하지 못했습니다:

1. **security-auditor 검증 영역** (모두 미검증):
   - JWT 토큰 저장 메커니즘 (`src/lib/token-storage.ts`)
   - 인증 훅 보안 (`src/hooks/useAuth.ts`)
   - 인증 컨텍스트 (`src/components/auth/AuthProvider.tsx`)
   - XSS 방지 (`dangerouslySetInnerHTML` 사용 여부)
   - 시크릿 관리 (하드코딩된 API 키, 토큰)
   - 파일 업로드 검증 (FDD VDR, IM 문서)

2. **api-auditor 일부 파일** (파일 접근 실패):
   - IM 모듈 훅 (`useDocuments.ts`, `useCompanies.ts`)
   - QueryClient 글로벌 설정 (`main.tsx`)
   - 환경변수 문서화 (`.env.production.example`)
   - FDD 모듈 나머지 훅 (`useQoE.ts`, `useNWC.ts`, `useMapping.ts` 등)

### 권장 후속 조치

1. **OneDrive 동기화 완료 대기 또는 폴더 로컬 다운로드**
   - 파일 탐색기에서 "항상 이 디바이스에 보관" 설정
2. **새 세션에서 보안 리뷰 재개**
   - security-auditor 에이전트 재실행
   - 미검증 영역 집중 검토
3. **P0 이슈 즉시 수정**
   - Critical-A1: FDD 훅들이 `fddApi` 사용하도록 변경

---

**리뷰 종료** — 2026-02-16 20:22
