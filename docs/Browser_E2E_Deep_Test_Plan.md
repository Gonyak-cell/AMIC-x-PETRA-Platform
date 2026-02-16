# 브라우저 E2E 검증 구현 계획

> 작성일: 2026-02-12 09:43:17

## Context

이전 세션에서 수행한 E2E 검증은 curl로 라우트별 HTTP 200 OK만 확인한 수준이었다.
React SPA가 JS를 실행하고, API를 호출하며, 데이터를 DOM에 렌더링하는 과정은 검증하지 못했다.

이 계획은 Playwright를 활용하여 실제 브라우저에서 React 앱이 정상 동작하는지 검증하는 "deep" 테스트를 추가한다.
기존 8개 smoke 테스트 파일(32+ 테스트)은 그대로 유지하고, 새로운 deep 테스트를 병렬로 추가한다.

**핵심 전략:** `page.route()` API 모킹으로 백엔드 없이도 결정적(deterministic) 테스트 실행 가능.

---

## 파일 구조 (신규 11개 파일)

```
e2e/
  fixtures/
    auth.fixture.ts          ← 기존 유지
    test-data.ts             ← 기존 유지
    console-monitor.ts       ← NEW: console/pageerror 캡처
    api-mocks.ts             ← NEW: page.route() 모킹 헬퍼 + 데이터
    test-base.ts             ← NEW: consoleMonitor 통합 fixture
  pages/
    dashboard.page.ts        ← 기존 유지
    fdd-deals.page.ts        ← 기존 유지
    login.page.ts            ← 기존 유지
    sidebar.page.ts          ← 기존 유지
    analytics.page.ts        ← NEW
    search-palette.page.ts   ← NEW
    kiis-companies.page.ts   ← NEW
    im-documents.page.ts     ← NEW
  tests/
    (기존 8개 유지)
    browser-health.spec.ts   ← NEW: JS 에러 + 하이드레이션 검증
    dashboard-deep.spec.ts   ← NEW: 대시보드 데이터 검증
    search-deep.spec.ts      ← NEW: 글로벌 검색 deep 검증
    analytics-deep.spec.ts   ← NEW: 애널리틱스 KPI + 차트
    fdd-deep.spec.ts         ← NEW: FDD 딜 목록 데이터
    kiis-deep.spec.ts        ← NEW: KIIS 기업 목록 데이터
    im-deep.spec.ts          ← NEW: IM 문서 목록 데이터
```

---

## Phase 1: 인프라 (Fixtures)

### 1-1. `e2e/fixtures/console-monitor.ts`

`page.on('console')` + `page.on('pageerror')` 리스너를 부착하여 JS 에러를 수집.

- `errors: string[]` — `console.error` 수집
- `unhandledExceptions: string[]` — 미처리 예외 수집
- `assertNoErrors()` — 필터링 후 에러 있으면 throw
- **필터링 대상 (benign):** `favicon.ico`, `DevTools`, `ResizeObserver loop`
- 참조: `src/components/analytics/AnalyticsChartPanel.tsx` — Recharts → ResizeObserver 에러 발생 가능

### 1-2. `e2e/fixtures/api-mocks.ts`

`page.route()`를 사용하여 모든 API 엔드포인트를 모킹. 기존 MSW 목 데이터(`src/test/mocks/data.ts`)를 기반으로 하되, E2E 환경에서는 직접 JSON으로 정의 (Vite path alias 미지원).

**모킹할 엔드포인트:**

| 패턴 | 용도 | 응답 소스 |
|------|------|-----------|
| `**/api/fdd/auth/me` | 인증 확인 | `mockUser` (admin) |
| `**/api/fdd/deals*` | FDD 딜 목록 | `mockDeals` (2건: ACTIVE, DRAFT) |
| `**/api/fdd/health` | FDD 상태 | `{ status: "ok" }` |
| `**/api/fdd/notifications` | 알림 | `mockNotifications` (2건) |
| `**/api/fdd/exports*` | 내보내기 | `mockExports` |
| `**/api/fdd/audit-logs*` | 감사 로그 | `mockAuditLogs` |
| `**/api/kiis/companies*` | KIIS 기업 | `mockCompanies` (삼성전자, SK하이닉스) |
| `**/api/kiis/alerts/unread-count` | 알림 수 | `{ count: 3 }` |
| `**/api/kiis/health` | KIIS 상태 | `{ status: "ok" }` |
| `**/api/kiis/dashboard/summary` | 대시보드 요약 | `mockDashboardSummary` |
| `**/api/kiis/search*` | 검색 | `mockKiisSearchResults` |
| `**/api/kiis/deals/by-sector*` | 섹터별 딜 | `mockSectorData` |
| `**/api/kiis/deals/trends*` | 딜 트렌드 | `mockDealTrends` |
| `**/api/im/documents*` | IM 문서 | `mockDocuments` (삼성전자 IM, SK IM) |
| `**/api/im/health` | IM 상태 | `{ status: "ok" }` |
| `**/api/fdd/auth/users` | 유저 목록 | `[]` |

**함수:**

- `mockAllApis(page)` — 위 모든 엔드포인트 일괄 모킹
- `mockFddDeals(page, data?)` — FDD 딜만 선택적 모킹
- `mockHealthEndpoints(page, overrides?)` — health 엔드포인트만, 에러 주입 가능
- `mockSearchApis(page, data?)` — 검색 관련만

### 1-3. `e2e/fixtures/test-base.ts`

기존 `auth.fixture.ts`의 `test`를 확장하여 `consoleMonitor` fixture 추가:

```typescript
export const test = base.extend<{ consoleMonitor: ConsoleMonitor }>({
  consoleMonitor: async ({ page }, use) => {
    const monitor = attachConsoleMonitor(page);
    await use(monitor);
  },
});
```

### 1-4. `playwright.config.ts` 수정

`chromium-mocked` 프로젝트 추가 — setup 의존성 없이 인라인 `storageState` 사용:

```typescript
{
  name: "chromium-mocked",
  testMatch: /.*-deep\.spec\.ts/,
  use: {
    ...devices["Desktop Chrome"],
    storageState: {
      cookies: [],
      origins: [{
        origin: "http://localhost:5173",
        localStorage: [{ name: "access_token", value: "mock-token" }],
      }],
    },
  },
  // setup 의존성 없음 — api-mocks가 auth/me를 모킹
}
```

---

## Phase 2: Page Objects (4개)

### 2-1. `e2e/pages/analytics.page.ts`

참조: `src/pages/analytics/AnalyticsPage.tsx`, `ModuleKpiSection.tsx`, `AnalyticsChartPanel.tsx`

- `heading`: h1 "Cross-Module Analytics"
- `fddSection`: h3 "Auto FDD"
- `kiisSection`: h3 "KIIS"
- `imSection`: h3 "IM Generator"
- `kpiCards`: text 매칭 — "Total Deals", "Active Deals", "Companies", "Funds", "Total Documents" 등
- `charts`: `.recharts-responsive-container` 내 SVG
- `errorBanner`: "backend is unreachable" 텍스트
- `filterBar`: "7d", "30d", "90d" 버튼들
- **메서드:** `goto()`, `expectLoaded()`, `expectChartsRendered()`, `expectErrorBanner(module)`

### 2-2. `e2e/pages/search-palette.page.ts`

참조: `src/components/search/CommandPalette.tsx`

- `dialog`: `[role="dialog"][aria-label="Global search"]`
- `searchInput`: `[role="combobox"][aria-label="Search input"]`
- `resultItems`: `[data-search-item]`
- `moduleBadges`: Badge 내 "FDD", "KIIS", "IM" 텍스트
- `loadingText`: "Searching..."
- `emptyState`: `No results found for`
- `recentHeader`: "Recent Searches"
- **메서드:** `open()` (Ctrl+K), `close()` (Escape), `search(query)`, `expectResultCount(n)`, `expectResultContains(text)`, `selectResult(index)`

### 2-3. `e2e/pages/kiis-companies.page.ts`

참조: `src/modules/kiis/pages/CompanyListPage.tsx`

- `heading`: h1 "Companies"
- `searchInput`: `label="Search"`
- `marketFilter`: `label="Market"`
- `dataTable`: `table` 또는 `[role='table']`
- `tableRows`: `table tbody tr`
- `emptyState`: "No companies found"
- **메서드:** `goto()`, `expectLoaded()`, `expectCompanyVisible(name)`, `searchFor(query)`

### 2-4. `e2e/pages/im-documents.page.ts`

참조: `src/modules/im/pages/DocumentListPage.tsx`

- `heading`: h1 "IM Projects"
- `kpiCards`: "Total Projects", "In Progress", "Completed", "Failed" 텍스트
- `dataTable`: `table`
- `emptyState`: "No IM projects yet"
- **메서드:** `goto()`, `expectLoaded()`, `expectDocumentVisible(name)`, `expectKpiValue(label, value)`

---

## Phase 3: 테스트 파일 (7개, ~40 테스트)

모든 deep 테스트는 `beforeEach`에서 `mockAllApis(page)` 호출 → 백엔드 불필요.

### 3-1. `browser-health.spec.ts` — JS 에러 + 하이드레이션 (8 테스트)

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | 대시보드 JS 에러 없음 | `/` → KPI 카드 렌더 대기 → `assertNoErrors()` |
| 2 | FDD 딜 목록 JS 에러 없음 | `/fdd/deals` → 테이블 대기 → `assertNoErrors()` |
| 3 | KIIS 기업 목록 JS 에러 없음 | `/kiis/companies` → 테이블 대기 → `assertNoErrors()` |
| 4 | IM 문서 목록 JS 에러 없음 | `/im` → 테이블 대기 → `assertNoErrors()` |
| 5 | 애널리틱스 JS 에러 없음 | `/analytics` → heading 대기 → `assertNoErrors()` |
| 6 | 관리자 페이지들 JS 에러 없음 | `/admin/users` → `/admin/activity` → `/settings/profile` 순회 |
| 7 | 검색 팔레트 JS 에러 없음 | Ctrl+K → 타이핑 → 닫기 → `assertNoErrors()` |
| 8 | 전체 모듈 순회 JS 에러 없음 | Dashboard→FDD→KIIS→IM→Analytics→Dashboard 네비게이션 |

### 3-2. `dashboard-deep.spec.ts` — 대시보드 데이터 (6 테스트)

참조: `DashboardPage.tsx` — KPI 레이블: "Active FDD Deals", "Watchlist Alerts", "IM In Progress", "Draft Deals"
에러 시 값: "—" (em dash)

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | KPI 카드에 API 데이터 수치 표시 | `mockDeals`(1 ACTIVE, 1 DRAFT) → "1" 표시 확인 |
| 2 | 빈 데이터 → KPI 0 표시 | 빈 배열 모킹 → "0" 확인 |
| 3 | 모듈 상태 Connected 표시 | health 200 모킹 → "Connected" × 3 |
| 4 | 모듈 상태 Unreachable 표시 | FDD health 500 모킹 → "Unreachable" 1개 |
| 5 | API 에러 시 KPI "—" 표시 | FDD `/deals` 500 → "—" 확인 |
| 6 | Quick Action 네비게이션 | "New Deal" 클릭 → URL `/fdd/deals/new` 확인 |

### 3-3. `search-deep.spec.ts` — 글로벌 검색 (6 테스트)

참조: `CommandPalette.tsx` — 최소 2글자, 300ms 디바운스, `data-search-item` 속성

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | 팔레트 열림 + 입력 포커스 | Ctrl+K → dialog visible, combobox focused |
| 2 | 검색어 입력 → 결과 렌더링 | "test" 입력 → `[data-search-item]` 요소 존재 확인 |
| 3 | 모듈별 Badge 표시 | 결과에 "FDD", "KIIS", "IM" Badge 텍스트 |
| 4 | 결과에 목 데이터 이름 표시 | "Project Alpha", "삼성전자" 등 텍스트 확인 |
| 5 | 결과 클릭 → 페이지 이동 | 첫 번째 결과 클릭 → URL 변경 확인 |
| 6 | 결과 없음 → 빈 상태 메시지 | 빈 결과 모킹 → "No results found for" 확인 |

### 3-4. `analytics-deep.spec.ts` — 애널리틱스 KPI + 차트 (5 테스트)

참조: `AnalyticsPage.tsx` → `ModuleKpiSection.tsx` + `AnalyticsChartPanel.tsx`
KPI 섹션 h3: "Auto FDD", "KIIS", "IM Generator"
차트: `TrendLineChart`, `FinancialBarChart` (Recharts 기반)

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | 3개 모듈 KPI 섹션 렌더링 | "Auto FDD", "KIIS", "IM Generator" heading 확인 |
| 2 | FDD KPI 수치 정확 | `mockDeals`(2건) → "Total Deals" = "2", "Active Deals" = "1" |
| 3 | KIIS KPI 수치 정확 | `mockDashboardSummary` → "Companies" = "150", "Funds" = "45" |
| 4 | 차트 SVG 렌더링 확인 | `.recharts-responsive-container svg` 존재 + `path`/`rect` 자식 확인 |
| 5 | 백엔드 에러 → 에러 배너 | FDD 500 모킹 → "FDD backend is unreachable" 텍스트 |

### 3-5. `fdd-deep.spec.ts` — FDD 딜 목록 (5 테스트)

참조: `DealListPage.tsx` — heading "Deals", 컬럼: Deal Name, Type, Currency, Reference Date, Team, Status
KPI: "Total Deals", "Active", "Draft", "Archived"

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | 테이블에 딜 이름 렌더링 | "Project Alpha", "Project Beta" 텍스트 확인 |
| 2 | KPI 카드 수치 정확 | "Total Deals" = "2", "Active" = "1", "Draft" = "1", "Archived" = "0" |
| 3 | 컬럼 헤더 표시 | "Deal Name", "Type", "Currency", "Reference Date", "Status" |
| 4 | 상태 Badge 렌더링 | "ACTIVE", "DRAFT" Badge 텍스트 |
| 5 | 빈 딜 → EmptyState | 빈 배열 모킹 → "No deals yet" 확인 |

### 3-6. `kiis-deep.spec.ts` — KIIS 기업 목록 (4 테스트)

참조: `CompanyListPage.tsx` — heading "Companies", 컬럼: Company, Stock Code, Market, CEO, Industry

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | 테이블에 기업명 렌더링 | "삼성전자", "SK하이닉스" 텍스트 확인 |
| 2 | 마켓 Badge 표시 | "KOSPI" Badge 텍스트 |
| 3 | 컬럼 헤더 표시 | "Company", "Stock Code", "Market", "CEO" |
| 4 | 빈 결과 → EmptyState | 빈 배열 모킹 → "No companies found" 확인 |

### 3-7. `im-deep.spec.ts` — IM 문서 목록 (4 테스트)

참조: `DocumentListPage.tsx` — heading "IM Projects", KPI: "Total Projects", "In Progress", "Completed", "Failed"
`DocumentStatusBadge` 컴포넌트로 상태 표시

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | 테이블에 프로젝트명 렌더링 | "Samsung IM", "SK IM" 텍스트 확인 |
| 2 | KPI 카드 수치 정확 | "Total Projects" = "2", "In Progress" = "1", "Completed" = "1" |
| 3 | 상태 표시 | "COMPLETED", "GENERATING" 텍스트 |
| 4 | 빈 문서 → EmptyState | 빈 배열 모킹 → "No IM projects yet" 확인 |

---

## Phase 4: 설정 변경

### `playwright.config.ts`

- `chromium-mocked` 프로젝트 추가 (setup 의존성 없음, `*-deep.spec.ts`만 매칭)
- 인라인 `storageState`로 mock 토큰 주입

### `package.json`

- `"test:e2e:deep"` 스크립트 추가: `playwright test --project=chromium-mocked`

---

## 실행 방법

```bash
# Mock 모드 (백엔드 불필요, CI용)
npm run test:e2e:deep

# 전체 (기존 smoke + deep, 백엔드 필요 for smoke)
npm run test:e2e

# UI 모드로 디버깅
npx playwright test --project=chromium-mocked --ui
```

---

## 구현 순서

1. `console-monitor.ts` → `api-mocks.ts` → `test-base.ts` (인프라)
2. Page Objects 4개 (`analytics`, `search-palette`, `kiis-companies`, `im-documents`)
3. `playwright.config.ts` + `package.json` 수정
4. 테스트 파일 7개 (`browser-health` → `dashboard` → `search` → `analytics` → `fdd` → `kiis` → `im`)
5. `npx playwright test --project=chromium-mocked` 실행으로 전체 검증

---

## 핵심 참조 파일

| 파일 | 용도 |
|------|------|
| `data.ts` | 목 데이터 원본 (`api-mocks.ts`에 복제) |
| `handlers.ts` | API 라우트 패턴 참조 |
| `DashboardPage.tsx` | KPI 레이블/에러 표시 ("—") |
| `useDashboard.ts` | 대시보드 API 호출 패턴 |
| `CommandPalette.tsx` | 검색 UI 셀렉터 |
| `useGlobalSearch.ts` | 검색 API 호출 (3모듈 병렬) |
| `AnalyticsPage.tsx` | 애널리틱스 구조 |
| `ModuleKpiSection.tsx` | KPI 섹션 레이블/에러 배너 |
| `AnalyticsChartPanel.tsx` | 차트 4종 구조 |
| `DealListPage.tsx` | FDD 테이블 컬럼/KPI |
| `CompanyListPage.tsx` | KIIS 테이블 컬럼/필터 |
| `DocumentListPage.tsx` | IM 테이블 컬럼/KPI |
| `playwright.config.ts` | Playwright 설정 |
