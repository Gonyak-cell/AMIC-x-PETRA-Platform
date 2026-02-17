# Platform 공통 레이어 코드 리뷰 — 보충 (Session 2)

> **리뷰 일시**: 2026-02-13 12:22
> **리뷰어**: Claude Code (Opus 4.6)
> **기존 문서**: `20260213_0957_Platform_Code_Review.md` (25건)
> **방법론**: 3개 탐색 에이전트 분석 → 소스코드 직접 검증 → 오탐 제거
> **범위**: 기존 리뷰에서 미다룬 Layout, UI 컴포넌트, Sentry, format 유틸, 접근성

---

## 요약

| 심각도 | 건수 |
|--------|------|
| Major | 5 |
| Minor | 10 |
| ~~오탐~~ | ~~3~~ |
| **합계** | **15** |

> 에이전트 제안 ~60건 중 기존 리뷰 중복·오탐 제거 후 15건 신규 확인.

---

## 에이전트 오탐 제거 (3건)

| 에이전트 주장 | 제거 사유 |
|---|---|
| client.ts:43-46 auth endpoint URL 매칭 실패 (HIGH) | `original.url`은 axios config의 상대 경로 (`"/auth/me"`)이므로 정상 매칭 |
| main.tsx MSW 오류 시 앱 미렌더 (MEDIUM) | try-catch (line 36-45)가 이미 에러를 처리하고 정상 return |
| AppShell ESC 핸들러 매 토글마다 재등록 (HIGH) | 이벤트 리스너 재등록 비용 무시할 수준, 실질 성능 영향 없음 |

---

## 1. Major 이슈 (5건)

### S1. SentryErrorBoundary — error.message 사용자 노출 (정보 유출)

- **파일**: `src/components/SentryErrorBoundary.tsx:12-13,23`
- **심각도**: Major
- **문제**: `error.message`를 그대로 UI에 표시. 내부 API URL, 서버 경로, 사용자 ID 등 민감 정보가 포함될 수 있음.

```typescript
// line 12-13
const message =
  error instanceof Error ? error.message : "An unexpected error occurred.";

// line 23 — 사용자에게 직접 노출
<p className="text-sm text-text-secondary mb-4">{message}</p>
```

- **수정안**: 프로덕션에서는 일반 메시지만 표시, 상세 정보는 Sentry로만 전송.

```diff
- const message =
-   error instanceof Error ? error.message : "An unexpected error occurred.";
+ const message = import.meta.env.PROD
+   ? "예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
+   : error instanceof Error ? error.message : "An unexpected error occurred.";
```

---

### S2. client.ts — refresh 실패 시 네트워크 에러 vs 인증 만료 미구분

- **파일**: `src/api/client.ts:78-82`
- **심각도**: Major
- **관련**: 기존 M3(AuthProvider의 `/auth/me` 401 vs 5xx)과 동일 패턴, 다른 위치
- **문제**: refresh 요청의 catch 블록이 모든 에러를 동일하게 처리. 일시적 네트워크 장애에도 토큰을 삭제하고 강제 로그아웃시킴.

```typescript
// line 78-82
} catch {  // ← 네트워크 에러도 인증 만료와 동일 처리
  clearTokens();
  emitForceLogout();
  return Promise.reject(error);
}
```

- **수정안**: 401만 강제 로그아웃, 나머지는 토큰 유지 후 원본 에러 반환.

```diff
- } catch {
+ } catch (refreshErr) {
+   const is401 = axios.isAxiosError(refreshErr) && refreshErr.response?.status === 401;
+   if (is401) {
      clearTokens();
      emitForceLogout();
+   }
    return Promise.reject(error);
  }
```

---

### S3. 모바일 사이드바 — 포커스 트랩 없음 (WCAG 2.1 AA 위반)

- **파일**: `src/components/layout/AppShell.tsx:112-128`
- **심각도**: Major
- **문제**: 모바일 사이드바 오픈 시 키보드 포커스가 사이드바 내부에 갇히지 않음. Tab 키로 오버레이 뒤의 메인 콘텐츠에 접근 가능. WCAG 2.1 Level AA "Focus Order" 위반.

```typescript
// line 112-128 — 오버레이는 있으나 포커스 트랩 없음
{isMobile && (
  <>
    <SidebarOverlay isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
    <div id="mobile-sidebar" className={cn(...)}>
      <Sidebar onNavItemClick={() => setSidebarOpen(false)} />
    </div>
  </>
)}

// line 132 — 메인 콘텐츠에 포커스 차단 없음
<main id="main-content" className="flex-1 bg-bg-cool">
```

- **수정안**: `inert` 속성으로 메인 콘텐츠 비활성화.

```diff
  {/* Main Content */}
- <main id="main-content" className="flex-1 bg-bg-cool">
+ <main
+   id="main-content"
+   className="flex-1 bg-bg-cool"
+   {...(isMobile && sidebarOpen ? { inert: "" } : {})}
+ >
```

> `inert`는 모든 모던 브라우저 지원 (Chrome 102+, Firefox 112+, Safari 15.5+). `inert` 속성 적용 시 해당 요소 및 자손에 대한 키보드/포인터 이벤트와 접근성 트리 접근이 차단됨.

---

### S4. useAnalyticsTimeSeries — moduleFilter 미적용

- **파일**: `src/hooks/useAnalytics.ts:223-280`
- **심각도**: Major
- **문제**: `useAnalyticsKpis`는 `moduleFilter`로 불필요한 쿼리를 비활성화하지만, `useAnalyticsTimeSeries`는 `filter.module`을 무시하고 항상 FDD + IM 데이터를 모두 fetch.

```typescript
// useAnalyticsKpis (line 149): enabled 조건 있음
enabled: !moduleFilter || moduleFilter === "fdd",

// useAnalyticsTimeSeries (line 226-246): enabled 조건 없음 — 항상 전부 fetch
queries: [
  { queryKey: ["analytics", "fdd-deals"], queryFn: async () => { ... } },    // 항상 활성
  { queryKey: ["analytics", "im-documents"], queryFn: async () => { ... } }, // 항상 활성
]
```

- **수정안**: `useAnalyticsKpis`와 동일한 `enabled` 조건 추가.

```diff
+ const moduleFilter = filter?.module;
+
  queries: [
    {
      queryKey: ["analytics", "fdd-deals"],
      queryFn: async () => { ... },
      staleTime: 60_000,
+     enabled: !moduleFilter || moduleFilter === "fdd",
    },
    {
      queryKey: ["analytics", "im-documents"],
      queryFn: async () => { ... },
      staleTime: 60_000,
+     enabled: !moduleFilter || moduleFilter === "im",
    },
  ],
```

---

### S5. formatAmount — Infinity 미처리

- **파일**: `src/lib/format.ts:15-16`
- **심각도**: Major
- **문제**: `parseFloat("Infinity")` → `Infinity` (NaN 아님) → NaN 체크 통과 → `Infinity.toLocaleString()` 실행 → 브라우저별 비결정적 결과. `formatPercent`(line 49), `formatCompact`(line 110)에도 동일 패턴 존재.

```typescript
// line 15-16
const num = typeof value === "string" ? parseFloat(value) : value;
if (isNaN(num)) return "-";  // Infinity는 NaN이 아니므로 통과
```

- **수정안**: `isFinite()` 사용 — `NaN`, `Infinity`, `-Infinity` 모두 `false` 반환.

```diff
  // formatAmount (line 16)
- if (isNaN(num)) return "-";
+ if (!isFinite(num)) return "-";

  // formatPercent (line 49)
- if (isNaN(num)) return "-";
+ if (!isFinite(num)) return "-";

  // formatCompact (line 110)
- if (isNaN(num)) return "-";
+ if (!isFinite(num)) return "-";
```

---

## 2. Minor 이슈 (10건)

### s1. formatDate — 혼합 로케일 (en-US vs ko-KR)

- **파일**: `src/lib/format.ts:71-80`
- **심각도**: Minor
- **문제**: `"long"` 포맷은 `ko-KR` → "2026년 2월 13일", `"month"`/`"short"`는 `en-US` → "Feb 2026", "02/13/2026". 동일 페이지에서 혼재 시 UX 일관성 저하.

---

### s2. Breadcrumbs — 구분자 아이콘 aria-hidden 누락

- **파일**: `src/components/ui/Breadcrumbs.tsx:26-28`
- **심각도**: Minor
- **문제**: `ChevronRight` 아이콘에 `aria-hidden="true"` 없음. 스크린리더가 구분자를 "image" 또는 아이콘 이름으로 읽을 수 있음.
- **수정안**: `<ChevronRight aria-hidden="true" className="..." />`

---

### s3. KpiCard — cursor-pointer 지정이나 onClick 없음 (false affordance)

- **파일**: `src/components/ui/KpiCard.tsx:60`
- **심각도**: Minor
- **문제**: `hoverLift && "hover-lift cursor-pointer"` — 마우스 커서가 pointer로 변하지만 클릭 핸들러가 없어 사용자 혼란.
- **수정안**: `cursor-pointer`를 제거하거나, `onClick` prop 추가.

---

### s4. LiveRegion — 100ms setTimeout 해킹

- **파일**: `src/components/ui/LiveRegion.tsx:35-39`
- **심각도**: Minor
- **문제**: 동일 메시지 재공지를 위해 `setTimeout(…, 100)` 사용. React 배치 업데이트나 느린 시스템에서 타이밍 미스 가능. 매직넘버.

---

### s5. Sentry — ResizeObserver 에러 필터 과도

- **파일**: `src/lib/sentry.ts:12-17`
- **심각도**: Minor
- **문제**: `event.exception?.values?.[0]?.value?.includes("ResizeObserver")` — "ResizeObserver" 문자열을 포함하는 모든 에러를 무조건 삭제. 실제 ResizeObserver 관련 버그도 무시됨.
- **수정안**: `"ResizeObserver loop completed with undelivered notifications"` 등 구체적 메시지로 한정.

---

### s6. console.log/warn이 프로덕션 코드에 잔존

- **파일**: `src/main.tsx:42,44` 외 다수
- **심각도**: Minor
- **문제**: MSW 관련 `console.log`/`console.warn`이 프로덕션 빌드에도 포함됨. `DEV` 체크 내부이므로 실제 노출은 없으나, 다른 위치(IssuesPage 등)의 `console.error`는 프로덕션에서도 실행됨.

---

### s7. Spinner — aria-label + sr-only 이중 선언

- **파일**: `src/components/ui/Spinner.tsx:22-26`
- **심각도**: Minor
- **문제**: `role="status" aria-label="Loading"` + `<span class="sr-only">Loading...</span>` → 스크린리더가 "Loading" 두 번 읽을 수 있음.
- **수정안**: sr-only span 제거, `aria-label`만 유지.

---

### s8. Card — h3 하드코딩

- **파일**: `src/components/ui/Card.tsx:52,63`
- **심각도**: Minor
- **문제**: 카드 제목이 항상 `<h3>`. 페이지 구조에 따라 `<h2>` 또는 `<h4>`가 적절할 수 있으나 변경 불가.
- **수정안**: `headingLevel` prop 추가 (선택적).

---

### s9. AppShell Ctrl+K 주석 — 코드 불일치

- **파일**: `src/components/layout/AppShell.tsx:64`
- **심각도**: Minor
- **문제**: 주석 `// Cmd/Ctrl+K to open command palette (always captures, even in inputs)` vs 실제 코드 line 70-72에서 `HTMLInputElement`/`HTMLTextAreaElement`/`isContentEditable` 제외. 주석이 틀림.
- **수정안**: 주석 수정 → `"(excludes input/textarea/contentEditable)"`.

---

### s10. useAnalytics — avgCycleDays 음수 가능

- **파일**: `src/hooks/useAnalytics.ts:60-65`
- **심각도**: Minor
- **문제**: `updated_at < created_at`인 데이터가 있으면 음수 사이클 일수 산출. `Math.max(0, ...)` 방어 없음.
- **수정안**:

```diff
- return sum + (updated - created) / (1000 * 60 * 60 * 24);
+ return sum + Math.max(0, updated - created) / (1000 * 60 * 60 * 24);
```

---

## 3. 기존 리뷰 대비 보충 요약

| 구분 | 기존 리뷰 | 이번 보충 | 합계 |
|------|-----------|-----------|------|
| Critical | 2건 | 0건 | 2건 |
| Major | 13건 | +5건 (S1-S5) | 18건 |
| Minor | 10건 | +10건 (s1-s10) | 20건 |
| **합계** | **25건** | **+15건** | **40건** |

---

## 4. 수정 우선순위 권장

### P0 (기존 C1, C2와 함께)
1. **S1** — SentryErrorBoundary 에러 메시지 노출 차단
2. **S5** — formatAmount/formatPercent/formatCompact `isFinite()` 적용 (각 1줄 수정)

### P1 (기존 M3 수정 시 함께)
3. **S2** — client.ts refresh catch 에러 분류

### P2
4. **S3** — 모바일 사이드바 포커스 트랩 (`inert` 속성)
5. **S4** — useAnalyticsTimeSeries moduleFilter 적용

### P3 (백로그)
6. s1~s10 — 리팩토링 시 함께 처리
