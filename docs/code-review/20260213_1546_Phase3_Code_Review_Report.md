# Phase 3: Infrastructure & Quality — 통합 코드 리뷰 리포트

**작성일**: 2026-02-13 15:44
**리뷰 대상**: AMIC x PETRA Platform 전체 (Frontend + Backend + Infra)
**리뷰 범위**: G1~G4 (테스트), H1~H3 (인프라), I1~I2 (성능), F3 (KIIS 외부 API)
**방법론**: Verified Claim Protocol (VCP) — 모든 파일을 Read 후 주장, 거부율 18~28%

---

## Executive Summary

| 카테고리 | 리뷰 항목 | Critical | Major | Moderate | Minor | 합계 |
|----------|----------|----------|-------|----------|-------|------|
| G1. 훅 유닛 테스트 | 14 | 2 | 2 | 6 | 4 | 14 |
| G2. 페이지/컴포넌트 테스트 | 11 | 0 | 3 | 4 | 4 | 11 |
| G3. E2E 인프라 | 11 | 0 | 1 | 3 | 5 | 9+2 PASS |
| G4. E2E 테스트 케이스 | 18 | 1 | 5 | 7 | 5 | 18 |
| H1. Docker & Compose | 18 | 0 | 4 | 6 | 8 | 18 |
| H2. Nginx 설정 | 13 | 0 | 3 | 4 | 6 | 13 |
| H3. CI/CD & 환경변수 | 13 | 2 | 4 | 3 | 4 | 13 |
| I1. 번들 분석 | 6 | 0 | 1 | 2 | 1 | 4+2 N/A |
| I2. 런타임 성능 | 10 | 0 | 0 | 3 | 6 | 9+1 N/A |
| F3. KIIS 외부 API | 15 | 1 | 5 | 5 | 4 | 15 |
| **합계** | **129** | **6** | **28** | **43** | **47** | **124** |

---

## Critical Issues (즉시 수정 필요) — 6건

### CI-1. Health Check 실패해도 배포 성공 처리
- **파일**: `.github/workflows/deploy.yml:47-50`
- **문제**: `curl -sf ... || echo "WARNING"` 패턴으로, 3개 백엔드 모두 죽어있어도 배포가 "성공"으로 기록됨
- **수정**: `|| { echo "ERROR"; exit 1; }` 로 변경

### CI-2. 배포 실패 시 롤백 전략 부재
- **파일**: `.github/workflows/deploy.yml:41-50`
- **문제**: `git pull` → `docker compose build` → `up -d` 후 실패해도 이전 상태 복원 불가
- **수정**: 배포 전 `PREV_COMMIT=$(git rev-parse HEAD)` 저장 + health check 실패 시 rollback

### G1-1. useAuth 테스트 QueryClientProvider 누락
- **파일**: `src/hooks/__tests__/useAuth.test.tsx:7-22`
- **문제**: `useAuth()` 내부에서 `useQueryClient()` 호출하지만 테스트 wrapper에 `QueryClientProvider` 없음
- **수정**: wrapper에 `QueryClientProvider` 추가

### G1-3. useWatchlist 테스트 데이터 형태 불일치
- **파일**: `src/modules/kiis/hooks/__tests__/useWatchlist.test.tsx:42-44`
- **문제**: `result.current.data`는 `{ total, items }` 객체인데 `toHaveLength(2)`로 배열처럼 assertion
- **수정**: `result.current.data?.items`로 접근

### G4-Q7. IM KPI 라벨 불일치
- **파일**: `e2e/tests/im-deep.spec.ts:26`
- **문제**: 테스트는 `"Total Projects"`를 찾지만, `DocumentListPage.tsx:118`의 실제 라벨은 `"Total"`
- **수정**: 테스트 라벨을 `"Total"`로 변경

### F3-1. DART ZIP/XML 파싱 에러 핸들링 부재
- **파일**: `KIIS/app/services/dart_service.py:78-81`
- **문제**: `zipfile.BadZipFile`, `IndexError`(빈 ZIP), `ET.ParseError` 모두 미처리. DART가 HTML 에러를 반환하면 crash
- **수정**: try/except로 `DARTAPIError` 래핑

---

## Major Issues (우선 수정) — 28건

### 테스트 (G1~G4) — 11건

| ID | 파일 | 문제 |
|----|------|------|
| G1-2 | `useAuth.test.tsx` | `login()` 함수 미테스트 (POST + GET /me + setAuthState) |
| G1-5 | `useDeals.test.tsx` | `useUpdateDeal` 미테스트 (optimistic update + rollback 로직) |
| G2-Q1 | `test-utils.tsx:62` | `renderWithProviders` 반환 queryClient가 렌더에 사용된 것과 다른 인스턴스 |
| G2-Q5 | `DealListPage.test.tsx:34-46` | KPI "correct values" 테스트가 실제 수치를 검증하지 않음 |
| G2-Q9 | `setup.ts:8-12` | afterEach에서 QueryClient 캐시 정리 없음 |
| G3-1 | `e2e/fixtures/api-mocks.ts:89-96` | mockDashboardSummary에 "리츠" count 누락 → analytics 테스트 실패 |
| G4-Q8 | `e2e/fixtures/api-mocks.ts:233-272` | mockDocuments에 `industry` 필드 누락 (Document 인터페이스와 불일치) |
| G4-Q13 | `e2e/tests/dashboard-deep.spec.ts:2` | 미사용 import (`mockHealthEndpoints`, `mockDeals`) |
| G4-Q14 | 5개 E2E 파일 | `mockAllApis` 후 override 패턴으로 route 핸들러 누적 |
| G4-Q17 | 5개 E2E 파일 | 전체 테스트에서 `test.afterEach` 부재 |
| G4-Q18 | `playwright.config.ts` | 글로벌 `timeout` 미설정 (기본 30s에 의존) |

### 인프라 (H1~H3) — 11건

| ID | 파일 | 문제 |
|----|------|------|
| H1-I01 | `IM Module/.../Dockerfile` | IM 컨테이너 root 실행 (`USER` 디렉티브 없음) |
| H1-I06 | `docker-compose.prod.yml:137-140` | Elasticsearch `xpack.security.enabled=false` in production |
| H1-I09 | dev→`JWT_SECRET`, prod→`FDD_JWT_SECRET`/`KIIS_SECRET_KEY`/`IM_SECRET_KEY` | JWT 시크릿 키 이름 불일치 (크로스 모듈 인증 실패 가능) |
| H1-I10 | `docker-compose.prod.yml:83-98` | KIIS prod에 `volumes: []` 오버라이드 누락 → dev 소스 마운트가 prod에서 유지 |
| H2-2 | `nginx/prod.conf:107-114` | KIIS proxy에 `client_max_body_size`/`proxy_read_timeout` 누락 |
| H2-3 | `nginx/prod.conf:68` | CSP `script-src 'unsafe-inline'` — XSS 보호 무효화 |
| H2-6 | `nginx/prod-nossl.conf:26-31` | CSP 헤더 완전 누락 (이것이 실제 prod에 마운트되는 config) |
| H3-3 | `deploy.yml:44-45` | 배포가 frontend/nginx만 대상, 백엔드 미포함 |
| H3-4 | `deploy.yml:47-49` | Health check URL과 nginx rewrite 규칙 불일치 |
| H3-5 | `.env.production.example` | Gemini API Key 누락 (IM Multi-Model Routing에 필요) |
| H3-12 | `docker-compose.prod.yml:87,124` | Redis 비밀번호 기본값 불일치 (client `:-}` vs server `:-redis}`) |

### 성능 & 외부 API (I1, F3) — 6건

| ID | 파일 | 문제 |
|----|------|------|
| I1-1 | `KiisRoutes.tsx:1-19` | 18개 페이지 전부 static import (React.lazy 미사용) |
| F3-2 | `dart_service.py:64` | `_request()` — non-JSON 응답 시 `JSONDecodeError` 미처리 |
| F3-4 | `scheduler.py:33-92` | `misfire_grace_time` 없음, error listener 없음 |
| F3-5 | `disclosure_service.py:169` + `dart_sync.py:41` | Double commit (서비스 내부 + 호출자) |
| F3-6 | `reputation_service.py:138` + `reputation_recalc.py:54` | Triple commit + 비원자적 워크플로 |
| F3-12 | `cache.py:48-50` | 캐시 hit 시 `dict` 반환 (Pydantic 모델이 아닌) — 간헐적 `AttributeError` |

---

## Moderate Issues — 43건

### 테스트 (17건)

| ID | 파일 | 요약 |
|----|------|------|
| G1-4 | `handlers.ts:54-78,137-151,197-220` | MSW POST 핸들러 request body 미검증 |
| G1-6 | `useDocuments.test.tsx:73-92` | 폴링 동작 미검증 (refetchInterval) |
| G1-8 | 다수 테스트 파일 | 401/404/422 에러 시나리오 미테스트 (500만 테스트) |
| G1-9 | `useSearch.test.tsx:70-79` | 쿼리 파라미터 전달 미검증 |
| G1-12 | `data.ts:306` | mockDocuments에 `offset`/`limit` 필드 누락 |
| G1-13 | `useWatchlist.test.tsx:100-117` | alerts 캐시 invalidation 미검증 |
| G2-Q2 | `test-utils.tsx:11` | `staleTime` 미설정 (비결정적 refetch 가능) |
| G2-Q3 | `setup.ts:16-25` | HTMLDialogElement 폴리필이 open 속성만 토글 |
| G2-Q4 | `setup.ts:30` | matchMedia `matches` 항상 false |
| G2-Q7 | `ImErrorBoundary.test.tsx` | `renderWithProviders` 미사용 |
| G3-2 | `auth.fixture.ts:12` | `page` 파라미터 타입 오류 (`Page`가 아닌 `TestType`) |
| G3-5 | `api-mocks.ts:360-387` | `mockAllApis` 이름과 달리 REIT/Fund/Manager 엔드포인트 누락 |
| G3-6 | `api-mocks.ts` 전체 | Mock 날짜 2025 하드코딩 (30d 기본 범위 밖) |
| G4-Q1 | `fdd-deep.spec.ts:22-32` | `locator("../..")` DOM 순회 취약 패턴 |
| G4-Q3 | `fdd-deep.spec.ts` | Deal 생성 플로우 E2E 미테스트 |
| G4-Q5 | `kiis-dashboard.page.ts:31-34` | KPI 값 로케이터 느슨한 매칭 |
| G4-Q10 | `search-palette.page.ts:37` | `waitForTimeout(500)` 안티패턴 |

### 인프라 (10건)

| ID | 파일 | 요약 |
|----|------|------|
| H1-I02 | `IM Dockerfile:57` | `COPY . .` 전체 소스 복사 (선별 COPY 필요) |
| H1-I03 | `docker-compose.yml` | frontend/nginx/fdd-api/fdd-pptx healthcheck 누락 |
| H1-I07 | `docker-compose.prod.yml:119-133` | KIIS Redis AOF persistence 누락 (IM Redis에는 있음) |
| H1-I11 | `docker-compose.prod.yml` | im-api prod volumes 오버라이드 누락 |
| H1-I12 | `amic-platform/Dockerfile` | 프론트엔드 nginx non-root 미설정 |
| H1-I14 | `nginx/prod.conf:42-50` | SSL server_name `_` + 하드코딩 cert 경로 충돌 |
| H2-4 | `nginx/prod.conf:68` | CSP `connect-src`가 Sentry에 너무 제한적 |
| H2-7 | `nginx/prod.conf:133-146` | `internal` health check — Docker/LB에서 접근 불가 |
| H2-13 | 모든 nginx config | Rate limiting 미설정 |
| H3-6 | `.env.production.example` | Elasticsearch 변수 누락 |

### 성능 & 외부 API (16건)

| ID | 파일 | 요약 |
|----|------|------|
| I1-2 | `DealWorkspacePage.tsx:1-14` | 11개 중첩 페이지 static import |
| I1-3 | `vite.config.ts:6-9` | `manualChunks` / `rollupOptions` 미설정 |
| I2-1 | `IssuesPage.tsx:300-324` | `handleResolve`/`handleDismiss` useCallback 미사용 |
| I2-5 | `DataTable.tsx` | 대규모 데이터셋 가상화 미지원 |
| I2-9 | `main.tsx:20-30` | `refetchOnWindowFocus` 글로벌 비활성화 미설정 |
| F3-3 | `kofia_service.py:66-71` | bare `Exception` catch + JSON 가정 |
| F3-7 | `database.py:24-26` | `get_db()` commit/rollback 없음 |
| F3-9 | `dart_sync.py:35-48` | DisclosureService `close()` 미호출 (HTTP 연결 누출) |
| F3-10 | `dart_sync.py:37-45` | 순차 처리 (동시성/배치 없음) |
| F3-11 | `reputation_recalc.py:45-62` | TOCTOU race condition |
| F3-13 | `dart_service.py:107-142` | tuple 반환값이 cache JSON round-trip에서 손실 |
| H3-7 | `ci.yml:108` | E2E가 chromium-mocked만 실행 |
| H3-8 | `ci.yml:32,51,82,104` | `npm ci` 4회 반복 |
| G4-Q9 | `im-deep.spec.ts` | IM 문서 생성 플로우 E2E 미테스트 |
| G4-Q15 | `dashboard-deep.spec.ts:30-65` | 빈 데이터 테스트에서 인라인 route 8개 설정 (비일관적) |
| G4-Q16 | `dashboard-deep.spec.ts:101-109` | Navigation 후 목적지 페이지 요소 미검증 |

---

## Priority Remediation Roadmap

### P0 — 즉시 수정 (배포 차단)
1. **CI-1, CI-2**: deploy.yml health check + rollback 추가
2. **H1-I10, H1-I11**: prod volumes 오버라이드 추가 (소스 마운트 제거)
3. **H3-12**: Redis 비밀번호 기본값 통일
4. **F3-12**: cache decorator 타입 보존 수정

### P1 — 1주 내 수정 (보안/정합성)
1. **H1-I01**: IM Dockerfile non-root USER 추가
2. **H1-I06**: ES xpack.security 활성화
3. **H2-3, H2-6**: CSP 헤더 추가/개선
4. **H1-I09**: JWT secret 키 이름 통일
5. **F3-1, F3-2**: DART API 에러 핸들링 추가
6. **F3-5, F3-6**: 이중 commit 제거 (서비스에서 commit 제거, 호출자에게 위임)

### P2 — 2주 내 수정 (테스트 품질)
1. **G1-1, G1-3**: Critical 테스트 버그 수정
2. **G2-Q1**: `renderWithProviders` QueryClient 인스턴스 통일
3. **G4-Q7**: IM KPI 라벨 수정
4. **G3-1**: mockDashboardSummary에 "리츠" 추가
5. **G3-6**: Mock 날짜를 동적(Date.now 기반)으로 변경

### P3 — 스프린트 내 수정 (성능/개선)
1. **I1-1**: KIIS 18페이지 React.lazy 적용
2. **I1-3**: Vite manualChunks 설정
3. **H2-13**: Nginx rate limiting 추가
4. **F3-4**: Scheduler misfire_grace_time + error listener
5. **F3-9**: 서비스 인스턴스 close() 패턴 정립

---

## 검증 투명성 (Verification Transparency)

| 에이전트 | 검증 가설 | 거부 가설 | 보고 이슈 | 거부율 |
|----------|----------|----------|----------|--------|
| G1 | 19 | 5 | 14 | 26% |
| G2 | 15 | 4 | 11 | 27% |
| G3 | 14 | 3 | 9+2 | 21% |
| G4 | 24 | 6 | 18 | 25% |
| H1 | 24 | 6 | 18 | 25% |
| H2 | 17 | 3 | 13 | 18% |
| H3 | 18 | 5 | 13 | 28% |
| I1 | 8 | 2 | 4+2 | 25% |
| I2 | 12 | 2 | 9+1 | 17% |
| F3 | 18 | 3 | 15 | 17% |
| **합계** | **169** | **39** | **124** | **23%** |

**평균 거부율 23%** — 전체 가설의 약 1/4이 실제 코드 검증 후 거부됨 (VCP의 anti-hallucination 효과 확인).

---

## 긍정적 측면

- **MSW 테스트 인프라**: `setup.ts`의 lifecycle 관리, `onUnhandledRequest: "warn"` 설정 적절
- **Playwright `serviceWorkers: "block"`**: MEMORY.md에 문서화된 critical gotcha가 정확히 구현됨
- **Auth token key 일치**: `autofdd_access_token`이 코드와 E2E config에서 정확히 매칭
- **React.lazy 모듈 레벨**: App.tsx에서 모듈별 lazy loading 올바르게 적용
- **API proxy rewrite 일관성**: Nginx 3개 config와 Vite proxy가 모두 동일한 rewrite 패턴 사용
- **CI pipeline 구조**: quality → test/build(병렬) → e2e 순서로 빠른 피드백 우선
- **recharts 중앙 집중화**: shared `components/charts/`에만 import (중복 없음)
- **useMemo 적용 (IssuesPage)**: 필터 객체 정확히 memoize됨
- **tailwind-merge 캐싱**: cn() 호출에 대한 LRU 캐시 내장 (v3.x)
