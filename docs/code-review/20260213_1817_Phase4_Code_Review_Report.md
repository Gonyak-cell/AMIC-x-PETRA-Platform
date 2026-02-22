# Phase 4: Foundations — 코드 리뷰 통합 보고서

> 생성일: 2026-02-13 18:15
> 범위: A3, A4, A5, A6, A7, F4 (6개 세션 병렬 실행)
> 참조: `docs/20260213_1344_Code_Review_Prompts_V3.md`
> 방법: 각 프롬프트를 독립 에이전트에서 병렬 실행, 모든 파일 Read 도구로 확인

---

## Executive Summary

| 카테고리 | 세션 | 파일 수 | Critical | Major | Moderate | Minor | 합계 |
|----------|------|------:|:--------:|:-----:|:--------:|:-----:|:----:|
| A3 | UI 기초 컴포넌트 | 8 | 0 | 1 | 1 | 3 | **5** |
| A4 | 데이터 표시 컴포넌트 | 7 | 0 | 0 | 4 | 9 | **13** |
| A5 | 레이아웃 & 네비게이션 | 7 | 0 | 0 | 3 | 3 | **6** |
| A6 | 글로벌 검색 & 팔레트 | 4 | 0 | 2 | 3 | 3 | **8** |
| A7 | 유틸리티 & 테스트 인프라 | 8 | 0 | 1 | 5 | 11 | **17** |
| F4 | KIIS ES & Redis | 10 | 2 | 3 | 4 | 3 | **12** |
| **합계** | | **44** | **2** | **7** | **20** | **32** | **61** |

---

## 심각도별 이슈 목록

### 🔴 Critical (2건)

| ID | 파일 | 이슈 | 세션 |
|----|------|------|------|
| F4-1 | KIIS docker-compose.yml + elasticsearch.py | **Nori 플러그인 미설치**: 도커 이미지에 `analysis-nori` 미포함 → 한국어 검색 불가 | F4 |
| F4-3 | KIIS search_service.py:122-201 | **Reindex 단건 인덱싱**: `es.index()` 루프 → bulk API 미사용, N+1 요청, 전체 테이블 메모리 로드 | F4 |

### 🟠 Major (7건)

| ID | 파일 | 이슈 | 세션 |
|----|------|------|------|
| A3-M1 | Modal.tsx:70-78 | **Double-close race**: 커스텀 ESC 핸들러 + 네이티브 `<dialog>` cancel 이벤트 충돌 | A3 |
| A6-M1 | useGlobalSearch.ts:89-109 | **IM 폴백 catch-all**: 모든 에러에서 200건 문서 로드 (400/422만 처리해야 함) | A6 |
| A6-M2 | CommandPalette.tsx:240 | **indexOf 참조 동등성**: `flatResults.indexOf(result)` — 참조 동등성 의존, O(n²) | A6 |
| A7-M1 | data.ts:290-303 | **mockImCompany.industry 타입 위반**: 브랜드 타입 `DartIndustryString`에 plain string 할당 | A7 |
| F4-2 | KIIS elasticsearch.py:24-26 | **Nori 분석기 필터 누락**: nori_part_of_speech, nori_readingform, lowercase 미설정 | F4 |
| F4-5 | KIIS docker-compose.prod.yml | **Redis maxmemory-policy 미설정**: 메모리 초과 시 OOM crash | F4 |
| F4-7 | KIIS elasticsearch.py:80 | **ES 인증/TLS 없음**: xpack.security.enabled=false, 프로덕션 취약 | F4 |

### 🟡 Moderate (20건)

| ID | 파일 | 이슈 | 세션 |
|----|------|------|------|
| A3-m1 | Modal.tsx:80 | `!open` 시 null 반환 — dialogRef 라이프사이클 fragile | A3 |
| A4-mR1 | DataTable.tsx:15 | `sortable` 속성 선언되었으나 정렬 로직 미구현 | A4 |
| A4-mR2 | DataTable.tsx:106-141 | 로딩 스켈레톤에 `role="status"` / `aria-busy` 미설정 | A4 |
| A4-mR7 | Pagination.tsx:13 | `<nav>` 랜드마크 및 `aria-label` 미설정 | A4 |
| A4-mR10 | Spinner.tsx:11 | `border-3` — Tailwind CSS 3 표준 클래스 아님 (lg 스피너 깨짐) | A4 |
| A5-2.2 | Sidebar.tsx:308 | Admin 섹션이 `/admin/*` 경로 접근 시 권한 없이도 표시 | A5 |
| A5-5.2 | ModuleSwitcher.tsx:82-108 | `role="listbox"` 선언되었으나 키보드 네비게이션 미구현 | A5 |
| A5-7.3 | App.tsx:42-158 | 최상위 catch-all 404 라우트 없음 | A5 |
| A6-m3 | CommandPalette.tsx:145-316 | `aria-modal="true"` 선언되었으나 focus trap 미구현 | A6 |
| A6-m4 | AppShell.tsx:64-80 | Ctrl+K가 토글 아닌 open만 수행 | A6 |
| A6-m5 | CommandPalette.tsx | 팔레트 오픈 시 body scroll lock 미적용 | A6 |
| A7-4.1 | ics.ts:22-33 | DTSTAMP 속성 누락 (RFC 5545 VEVENT 필수) | A7 |
| A7-4.2 | ics.ts:3-5 | formatIcsDate가 DATE-TIME 포맷 사용 (VALUE=DATE가 적합) | A7 |
| A7-7.1 | handlers.ts:44-46 | FDD deals 목록 핸들러가 배열 반환 (페이지네이션 래퍼 필요 가능성) | A7 |
| A7-7.2 | handlers.ts:54-78 | POST /deals `...body` 스프레드 순서 오류 — body 값이 기본값에 덮어쓰임 | A7 |
| A7-8.5 | data.ts:142-153 | 7개 mock 데이터 타입 어노테이션 미설정 | A7 |
| F4-4 | KIIS search_service.py:21-26 | 크로스인덱스 검색 시 필드 부스팅 미설정 | F4 |
| F4-6 | KIIS cache.py + dart_service.py | 캐시 무효화 전략 없음 (TTL 의존, 능동적 무효화 미구현) | F4 |
| F4-9 | KIIS rate_limit.py:120-158 | `_InMemoryStore` 만료 키 정리 미흡 → 무한 성장 | F4 |
| F4-10 | KIIS rate_limit.py:50-57 | RateLimitMiddleware가 별도 Redis 연결 생성 (공유 풀 미사용) | F4 |

### 🔵 Minor (32건)

<details>
<summary>전체 Minor 이슈 목록 (클릭하여 펼치기)</summary>

| ID | 파일 | 이슈 | 세션 |
|----|------|------|------|
| A3-L1 | Modal.tsx:49-53 | contentRef가 close 버튼 포함 패널 전체를 감싸 첫 포커스가 close 버튼으로 감 | A3 |
| A3-L2 | Select.tsx:57 | placeholder `<option>`에 `hidden` 속성 없음 | A3 |
| A3-L3 | Button.tsx:65-85 | 인라인 SVG 스피너 20줄 — 추출 가능 | A3 |
| A4-LR3 | DataTable.tsx:177 | `<th>`에 `scope="col"` 미설정 | A4 |
| A4-LR4 | DataTable.tsx:215 | `role="button"` on `<tr>` — `role="row"` 덮어쓰기 | A4 |
| A4-LR5 | DataTable.tsx:109,148,174 | 헤더 렌더링 로직 3회 중복 | A4 |
| A4-LR6 | KpiCard.tsx:9 | `value` prop이 string — 내장 포맷팅 없음 | A4 |
| A4-LR8 | Pagination.tsx:9-35 | 페이지 점프/첫째·마지막 버튼 없음 | A4 |
| A4-LR9 | Skeleton.tsx:8 | 기본 Skeleton에 a11y 속성 없음 (설계상 합성 컴포넌트가 처리) | A4 |
| A4-LR11 | Spinner.tsx:14-25 | `sr-only` 텍스트 없음 | A4 |
| A4-LR12 | LiveRegion.tsx:74-86 | Provider 미존재 시 silent no-op (console.warn 없음) | A4 |
| A4-LR13 | LiveRegion.tsx:32-41 | setTimeout 100ms 패턴 — 언마운트 시 stale setState (리스크 낮음) | A4 |
| A5-1.1 | AppShell.tsx:56-62 | ESC 핸들러가 CommandPalette와 충돌 가능 | A5 |
| A5-2.1 | Sidebar.tsx:128-131 | `<aside>`에 `role="navigation"` — 시맨틱 부정확 | A5 |
| A5-7.4 | App.tsx:133-156 | 샘플 페이지에 dev/admin 게이팅 없음 | A5 |
| A6-L6 | CommandPalette.tsx:176-180 | combobox input에 `aria-controls` 미설정 | A6 |
| A6-L7 | CommandPalette.tsx:61-68 | grouped 키 순서가 API 응답 순서에 의존 — 불확정적 | A6 |
| A6-L8 | CommandPalette.tsx:91-96 | `useCallback` 불필요 래핑 | A6 |
| A7-1.1 | format.ts:40-55 | formatPercent: "+0.00%" 엣지 케이스 (발생 가능성 낮음) | A7 |
| A7-1.2 | format.ts:94-99 | formatBytes: GB 범위 미지원 | A7 |
| A7-1.3 | format.ts:95 vs 13 | null 플레이스홀더 불일치 (em-dash vs hyphen) | A7 |
| A7-1.5 | format.ts:66-67 | formatDate: 타임존 오프셋 시 날짜 변경 가능성 (KST에선 안전) | A7 |
| A7-2.1 | statusVariant.ts:6-22 | "ARCHIVED" 상태가 neutral로 fall-through (의도적일 수 있음) | A7 |
| A7-3.1 | sentry.ts:3-18 | 프로덕션 전용 게이트 없음 (DSN 설정 여부에 의존) | A7 |
| A7-3.2 | sentry.ts:13 | beforeSend에서 첫 번째 exception만 확인 | A7 |
| A7-4.3 | ics.ts:40-51 | revokeObjectURL 동기 호출 — 이론적 race (실무상 안전) | A7 |
| A7-5.1 | setup.ts:16-25 | HTMLDialogElement 폴리필 OR 패턴 — jsdom 업데이트 시 fragile | A7 |
| A7-6.1 | test-utils.tsx:11 | staleTime: Infinity — refetch 테스트 불가 | A7 |
| A7-7.3 | handlers.ts:197-220 | IM POST 핸들러 vs FDD POST 핸들러 body 스프레드 순서 불일치 | A7 |
| F4-8 | KIIS elasticsearch.py:99, search_service.py:75 | ES 8.x `body` 파라미터 deprecated | F4 |
| F4-11 | KIIS elasticsearch.py:52-59 | ES 인덱스 매핑에 timestamp, multi-field 미설정 | F4 |
| F4-12 | KIIS cache.py:14 | 캐시 키 생성 시 `str()` 변환 — 타입 충돌 가능 | F4 |

</details>

---

## 세션별 상세 리뷰

### A3. UI 컴포넌트 — 기초 (Batch 1)

**대상 파일**: Button.tsx, Input.tsx, Select.tsx, Badge.tsx, Card.tsx, Modal.tsx, cn.ts, index.ts

**검증 완료 사항 (이슈 아님)**:
- ✅ `cn()`: twMerge + clsx 정상 사용 (이전 FP-HALLUC "단순 join" 확인 반박)
- ✅ Badge variants: `success | warning | error | info | neutral` 정확히 일치
- ✅ Card: onClick prop 없음 (문서 일치)
- ✅ Button: disabled 상태에서 네이티브 `disabled` 속성으로 이벤트 전파 차단
- ✅ Input: `forwardRef` + `useId()` 정상 구현
- ✅ index.ts: 15개 UI 컴포넌트 전부 export 완료

**주요 발견**: Modal.tsx에서 네이티브 `<dialog>` cancel 이벤트와 커스텀 ESC 핸들러 충돌 (Major)

---

### A4. UI 컴포넌트 — 데이터 표시 (Batch 2)

**대상 파일**: DataTable.tsx, KpiCard.tsx, EmptyState.tsx, Pagination.tsx, Skeleton.tsx, Spinner.tsx, LiveRegion.tsx

**검증 완료 사항 (이슈 아님)**:
- ✅ DataTable `keyField`: REQUIRED 확인 (line 26)
- ✅ `Column.key`: `Extract<keyof T, string> | (string & {})` — 실제로는 유니온 타입
- ✅ `onSelectAll`: 미존재 확인
- ✅ KpiCard variants: `default | positive | negative | caution` (Badge와 다름 확인)
- ✅ EmptyState: 이슈 없음

**주요 발견**: Spinner.tsx `border-3`가 Tailwind CSS 3 표준 클래스가 아님 → lg 스피너 시각적 깨짐 (Moderate)

---

### A5. 레이아웃 & 네비게이션

**대상 파일**: AppShell.tsx, Sidebar.tsx, PageHeader.tsx, HealthIndicator.tsx, ModuleSwitcher.tsx, main.tsx, App.tsx

**검증 완료 사항 (이슈 아님)**:
- ✅ HealthIndicator: React Query `refetchInterval`로 폴링 — useEffect cleanup 불필요
- ✅ main.tsx: StrictMode > SentryErrorBoundary > QueryClientProvider > BrowserRouter > AuthProvider 순서 정확
- ✅ App.tsx: 모든 lazy 라우트에 개별 Suspense 래핑
- ✅ PageHeader.tsx: 이슈 없음

**주요 발견**: App.tsx에 최상위 catch-all 404 라우트 없음 → 정의되지 않은 경로 접근 시 빈 페이지 (Moderate)

---

### A6. 글로벌 검색 & 커맨드 팔레트

**대상 파일**: useGlobalSearch.ts, CommandPalette.tsx, types/search.ts, AppShell.tsx(Ctrl+K)

**검증 완료 사항 (이슈 아님)**:
- ✅ 디바운스: 300ms setTimeout + cleanup 정상 구현
- ✅ ESC 키 핸들링: 정상 동작
- ✅ 모듈별 라우팅: FDD/KIIS/IM 경로 정확
- ✅ 빈 상태/로딩 상태: "Searching...", "No results found", 실패 모듈 amber 배너
- ✅ types/search.ts: 이슈 없음

**주요 발견**: IM 폴백이 catch-all로 모든 에러에서 200건 문서 로드 (Major), focus trap 미구현 (Moderate)

---

### A7. 유틸리티 & 테스트 인프라

**대상 파일**: format.ts, statusVariant.ts, sentry.ts, ics.ts, setup.ts, test-utils.tsx, handlers.ts, data.ts

**검증 완료 사항 (이슈 아님)**:
- ✅ format.ts `formatAmount`: `isFinite(num)` NaN 처리 정상
- ✅ setup.ts: MSW lifecycle, cleanup, localStorage.clear 정상
- ✅ test-utils.tsx: renderWithProviders 구조 정상
- ✅ statusVariant.ts: IM 모듈은 자체 DocumentStatusBadge 사용 → 미매핑 무관

**주요 발견**: data.ts mockImCompany.industry 브랜드 타입 위반 (Major), ics.ts RFC 5545 DTSTAMP 누락 (Moderate)

---

### F4. KIIS ElasticSearch & Redis

**대상 파일**: elasticsearch.py, redis.py, search_service.py, nlp_service.py + docker-compose, cache.py, rate_limit.py

**검증 완료 사항 (이슈 아님)**:
- ✅ 와일드카드 검색 (KIIS #2.4): `multi_match` + 명시적 필드 사용 → 이미 해결됨
- ✅ NLP 서비스: 감성 분석 로직 구조 정상

**주요 발견**:
1. Nori 플러그인 미설치 → 한국어 검색 완전 불가 (Critical)
2. Reindex 단건 인덱싱 → bulk API 미사용 (Critical)
3. Redis maxmemory-policy 미설정 (Major)
4. ES 인증/TLS 미설정 (Major)

---

## 우선순위 액션 아이템

### 즉시 수정 (Critical + Major)

1. **F4-1**: KIIS ES Docker 이미지에 `analysis-nori` 플러그인 설치
2. **F4-3**: `search_service.py` reindex를 `async_bulk` + 배치 DB 읽기로 전환
3. **F4-2**: Nori 분석기에 `nori_part_of_speech`, `nori_readingform`, `lowercase` 필터 추가
4. **F4-5**: Redis `maxmemory 256mb`, `maxmemory-policy allkeys-lru` 설정
5. **F4-7**: 프로덕션 ES에 X-Pack security 활성화
6. **A3-M1**: Modal.tsx ESC 핸들러를 `<dialog onCancel>` 패턴으로 교체
7. **A6-M1**: IM 검색 폴백을 HTTP 400/422에서만 동작하도록 축소
8. **A6-M2**: `indexOf` → 누적 인덱스 방식으로 전환
9. **A7-M1**: `mockImCompany.industry`에 `as DartIndustryString` 캐스트 추가

### 단기 개선 (Moderate)

10. **A4-mR10**: Spinner.tsx `border-3` → `border-[3px]` 또는 `border-4`
11. **A5-7.3**: App.tsx에 `<Route path="*">` 404 페이지 추가
12. **A6-m3**: CommandPalette에 focus trap 구현
13. **A6-m5**: 팔레트 오픈 시 `document.body.style.overflow = "hidden"` 추가
14. **A7-4.1/4.2**: ics.ts에 DTSTAMP 추가 + VALUE=DATE 포맷 사용
15. **A7-7.2**: handlers.ts POST /deals `...body` 스프레드를 마지막으로 이동

---

## 허위 발견(FP) 필터링 결과

총 **96개 가설** 검증, **37개 사전 필터링** (거부율 39%)

| 세션 | 검증 | 거부 | 보고 | 거부율 |
|------|:----:|:----:|:----:|:------:|
| A3 | 14 | 7 | 5 | 50% |
| A4 | 22 | 9 | 13 | 41% |
| A5 | 18 | 7 | 6 | 39% |
| A6 | 14 | 6 | 8 | 43% |
| A7 | 25 | 8 | 17 | 32% |
| F4 | 별도 집계 없음 | - | 12 | - |

주요 거부 사례:
- ❌ "cn()가 단순 join" → twMerge + clsx 사용 확인 (FP-HALLUC)
- ❌ "HealthIndicator cleanup 없음" → React Query가 자동 관리 (FP-CTX)
- ❌ "Modal에 aria-modal 없음" → `<dialog>` showModal()이 자동 제공 (FP-CTX)
- ❌ "디바운스 없음" → 300ms setTimeout 확인 (FP-IMPL)
- ❌ "와일드카드 검색 사용" → multi_match 사용 확인 (FP-IMPL, KIIS #2.4 해결됨)
