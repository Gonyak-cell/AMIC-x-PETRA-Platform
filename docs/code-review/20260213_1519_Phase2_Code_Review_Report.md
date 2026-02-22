# Phase 2: Module Completion — 코드 리뷰 통합 리포트

> 생성일: 2026-02-13 15:16
> 범위: 15개 프롬프트 (B1, B3, B4, B6, B7, B8, C1, C2, C3, C4, C5, C6, D2, D3, F2)
> 파일 수: ~80개 파일 리뷰
> 에이전트: 15개 독립 에이전트 병렬 실행

---

## Executive Summary

| 심각도 | 건수 | 비율 |
|---------|------|------|
| 🔴 Critical/High | **4** | 4% |
| 🟠 Major | **13** | 12% |
| 🟡 Moderate | **35** | 33% |
| 🔵 Minor | **53** | 51% |
| **합계** | **105** | 100% |

### Top 5 즉시 수정 항목

| 순위 | ID | 모듈 | 이슈 | 심각도 |
|------|-----|------|------|--------|
| 1 | F2-5.3 | FDD BE | `QoEStatus.COMPLETED` 존재하지 않는 enum 참조 → 500 에러 | 🔴 High |
| 2 | F2-2.1 | FDD BE | `create_definition` 버전 번호 race condition (SELECT FOR UPDATE 없음) | 🔴 Medium-High |
| 3 | C3-R4 | KIIS FE | NewsListPage `collected_count` 타입 불일치 → toast 항상 폴백 (실제 버그) | 🟠 Major |
| 4 | B4-R1 | FDD FE | DealListPage 모달 "Create Deal" 버튼이 form 바깥 → validation 우회 | 🟠 Major |
| 5 | C6-P1 | KIIS FE | KiisRoutes 18개 페이지 정적 import → 번들 크기 이슈 | 🟠 Major |

---

## 모듈별 상세 결과

---

### B1. FDD 훅 — Deal 관리

**파일**: useDeals.ts, useUploads.ts, useDefinitions.ts, useDeals.test.tsx
**쿼리키 프리픽스**: ✅ 전수 통과 (`["fdd", ...]`)

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | B1-9 | `useUpdateDeal` 테스트 완전 누락 — 낙관적 업데이트 + rollback 검증 없음 |
| 🟡 Moderate | B1-4 | Delete/Archive 뮤테이션 부재, `DealCreate`에 `status` 필드 없음 |
| 🟡 Moderate | B1-5 | 파일 업로드 progress 콜백 미구현 |
| 🟡 Moderate | B1-6 | 대용량 파일 클라이언트 사이드 크기 제한 없음 |
| 🟡 Moderate | B1-12 | useDeal, useCreateDeal 에러 케이스 테스트 부재 |
| 🔵 Minor | B1-1 | `onSettled` 중복 무효화 (fuzzy matching으로 이미 커버) |
| 🔵 Minor | B1-7 | useDefinitions `staleTime` 미설정 |
| 🔵 Minor | B1-8 | useDefinitions mutation 반환값 타입 캐스팅 누락 |
| 🔵 Minor | B1-10 | 테스트 간 QueryClient/wrapper 패턴 불일치 |
| 🔵 Minor | B1-13 | default `api` import 명시성 부족 |

---

### B3. FDD 훅 — 보조 기능

**파일**: useMapping.ts, useIssues.ts, useReportVersions.ts, useVdr.ts
**Session 3 수정**: ✅ tie-out 무효화 반영 확인, staleTime 1시간 적용 확인

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | B3-R11 | ReportVersionCard 다운로드 시 `window.open()` → JWT 인증 헤더 미전달 |
| 🟡 Moderate | B3-R7 | `useDismissIssue`에 `resolved_by` 미전달 (resolve와 비대칭) |
| 🟡 Moderate | B3-R9 | 버전 목록 정렬 로직 부재 — 백엔드 순서에 의존 |
| 🟡 Moderate | B3-R13 | VDR 폴더 트리 깊이 제한 미구현 |
| 🟡 Moderate | B3-R6 | `resolved_by` 타입 `string | undefined` vs `string | null` 불일치 |
| 🔵 Minor | B3-R3/R15 | 9개 mutation 전부 `onError` 콜백 없음 |
| 🔵 Minor | B3-R10 | 다운로드 URL `/api/fdd` 하드코딩 |
| 🔵 Minor | B3-R14 | VDR expand/collapse 상태 관리 훅 부재 |

---

### B4. FDD 페이지 — Deal Setup

**파일**: DealListPage.tsx, DealSetupWizard.tsx, ScopeSelector.tsx, DealListPage.test.tsx

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | B4-R1 | 모달 "Create Deal" 버튼이 `<form>` 바깥 → HTML `required` validation 우회 |
| 🟠 Major | B4-R2 | 위자드 "Create Deal" `disabled` 조건 불완전 (`period_start`/`period_end` 미확인) |
| 🟠 Major | B4-R3 | Next 버튼에 단계별 validation 없음 → 빈 필드로 다음 단계 진행 가능 |
| 🟡 Moderate | B4-R4 | 날짜 validation 경계값 확인 필요 |
| 🟡 Moderate | B4-R5 | Deal 목록에 필터링/정렬/검색 기능 전무 |
| 🟡 Moderate | B4-R6 | 모달 `INITIAL_FORM`에 `industry` 필드 누락 |
| 🟡 Moderate | B4-R7 | Step 3(Team) placeholder만 존재 — useTeamMembers 미연동 |
| 🔵 Minor | B4-R8 | ScopeSelector 3개 모두 해제 방지 로직 없음 |
| 🔵 Minor | B4-R9 | ScopeSelector 접근성 속성 부재 |
| 🔵 Minor | B4-Q1~Q3 | 테스트: KPI 값 미검증, Industry/모달 테스트 부재 |
| 🔵 Minor | B4-R10 | Deal 생성 경로 2개(모달 vs 위자드) — 전송 데이터 불일치 |
| 🔵 Minor | B4-R11 | Step indicator 클릭 이동 불가 |

---

### B6. FDD 페이지 — 보조 페이지

**파일**: DefinitionPage.tsx, MappingPage.tsx, UploadPage.tsx, IssuesPage.tsx
**Session 3 수정**: ✅ approved_by 반영 완료, ✅ IssuesPage useMemo 적용 완료

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | B6-R4 | UploadPage 클라이언트 측 파일 크기 제한 미구현 |
| 🟡 Moderate | B6-R3 | MappingPage KPI 계산 배열 3회 순회 |
| 🟡 Moderate | B6-R5 | 파일 업로드 HTTP 진행률 미표시 (axios `onUploadProgress` 미사용) |
| 🟡 Moderate | B6-R10 | MappingPage/UploadPage query 에러 상태 처리 누락 |
| 🟡 Moderate | B6-R12 | 4개 페이지 모두 Breadcrumbs 미사용 |
| 🟡 Moderate | B6-R2 | MappingPage suggestions 로컬 state — 페이지 이탈 시 소실 |
| 🔵 Minor | B6-R6 | UploadPage `formatBytes` 중복 (format.ts에 이미 존재) |
| 🔵 Minor | B6-R7 | 다중 파일 업로드 미지원 (`files[0]`만 처리) |
| 🔵 Minor | B6-R8 | IssuesPage 페이지네이션 미구현 (`limit: 100` 고정) |
| 🔵 Minor | B6-R9 | resolve 시 `resolution_note` 미전달 |
| 🔵 Minor | B6-R11 | UploadPage EmptyState 컴포넌트 미사용 (수동 구현) |
| 🔵 Minor | B6-R1 | DefinitionPage useAuth 구독 범위 (정보성) |

---

### B7. FDD 페이지 — Report & VDR

**파일**: ReportPage.tsx, VdrPage.tsx, ReportVersionCard.tsx, ReportVersionList.tsx, VdrFolderTree.tsx, VdrFolderItem.tsx
**Session 2 수정**: ✅ API 경로 수정 반영 확인, ✅ DOCX 형식 지원 반영 확인

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | B7-R1 | 리포트 생성 후 `invalidateQueries` 미호출 → 버전 목록 자동 갱신 안 됨 |
| 🟠 Major | B7-R2 | 버전 목록 최신순 정렬 로직 없음 — 서버 응답 순서 그대로 |
| 🟡 Moderate | B7-R3 | VdrFolderItem 재귀 깊이 제한 없음 |
| 🟡 Moderate | B7-A1 | ReportVersionCard 다운로드 `window.open()` → JWT 미전달 |
| 🟡 Moderate | B7-X1 | VDR ARIA 트리뷰 시멘틱 없음 (`role="tree"`, `aria-expanded`) |
| 🟡 Moderate | B7-X2 | ReportPage 라디오 버튼 `fieldset`/`legend` 없음 |
| 🔵 Minor | B7-R4 | Preview DataTable `keyField="type"` 중복 가능 |
| 🔵 Minor | B7-R5 | VdrPage 폴더 선택 시 파일 목록 미구현 (placeholder) |
| 🔵 Minor | B7-R6 | ReportPage 체크박스 4개 반복 코드 (DRY 위반) |
| 🔵 Minor | B7-R7 | VdrPage `dealId!` non-null assertion, null 가드 없음 |
| 🔵 Minor | B7-R8 | `file_format`이 open `string` 타입 — 유니온 미적용 |

---

### B8. FDD 타입 & 크로스모듈 통합

**파일**: industry.ts, deal.ts, report-version.ts, constants.ts, FddRoutes.tsx

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | B8-T1 | `deal.ts`에서 `IndustryType` 중복 정의 (공유 `IndustryId` 미사용) → 동기화 리스크 |
| 🟡 Moderate | B8-A1 | `ReportVersion.options` 타입이 BE보다 좁음 (`Record<string, boolean>` vs `dict`) |
| 🟡 Moderate | B8-R1 | FDD 내부 16개 페이지 전부 정적 import |
| 🟡 Moderate | B8-T2 | `file_format`이 `string` 타입 — BE는 `"pptx" | "docx"`만 허용 |
| 🔵 Minor | B8-R2 | constants.ts 타입-옵션 이중 관리 |
| 🔵 Minor | B8-R3 | DealSetupWizard navigate 경로 prefix 확인 필요 |
| 🔵 Minor | B8-A2 | ReportVersion에 `updated_at` 없음 (의도적 설계) |

---

### C1. KIIS 훅 — 코어 데이터

**파일**: useCompanies.ts, useSearch.ts, useSearch.test.tsx, company.ts

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | C1-A1 | **corpCode 포맷 검증 누락** — useCompanyDetail 등 4개 함수에서 `!!corpCode`만 체크. 같은 모듈의 useDisclosures/usePortfolio는 정규식 검증 적용 → 모듈 내 불일치 |
| 🟡 Moderate | C1-R1 | useSearch에 디바운스 없음 — 호출부에 위임 |
| 🟡 Moderate | C1-R2 | 평판 queryKey 네임스페이스 공유 (useCompanies + useAnalysis에 분산) |
| 🟡 Moderate | C1-Q1 | SearchBar 디바운스 통합 테스트 부재 |
| 🟡 Moderate | C1-R7 | `SearchResultItem.index`가 `string` — `SearchIndexType` union 미적용 |
| 🔵 Minor | C1-Q2 | useSearch 테스트 — MSW 핸들러가 type 파라미터 무시 |
| 🔵 Minor | C1-R4 | FE `corp_cls: CorpCls` vs BE `str | None` 차이 |
| 🔵 Minor | C1-R8 | useCompanies 단일 책임 원칙 부분 위반 (3개 도메인) |

---

### C2. KIIS 훅 — 금융 데이터

**파일**: useFunds.ts, useReits.ts, useManagers.ts, usePortfolio.ts, useDeals.ts

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | C2-1 | useFunds/useReits 쿼리키 구조적 충돌 가능성 (`"list"/"detail"` 세그먼트 없음) |
| 🟡 Moderate | C2-2 | useDeals corpCode 미검증 (`!!corpCode`만 사용) |
| 🟡 Moderate | C2-3 | useManagers corpCode 미검증 |
| 🟡 Moderate | C2-4 | 5개 파일 전체 staleTime 미설정 (금융 데이터 특성상 5~10분 권장) |
| 🔵 Minor | C2-5 | mutation onError/toast 미구현 |
| 🔵 Minor | C2-6 | useFundManagers에서 total 소실 (페이지네이션 정보 버림) |
| 🔵 Minor | C2-7 | usePortfolio mutation 3개에서 corpCode 미검증 |

**충돌 없음 확인**: useFundManagers(`"fund-managers"`) vs useManagers(`"managers"`) — 키 분리됨

---

### C3. KIIS 훅 — 뉴스 & 워치리스트

**파일**: useNews.ts, useWatchlist.ts, useSanctions.ts, useDisclosures.ts, useWatchlist.test.tsx

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟡 Moderate | C3-R1 | useAddToWatchlist 비대칭 무효화 — alerts 무효화 누락 |
| 🟡 Moderate | C3-R6 | useSanctions corpCode 검증 미비 |
| 🟡 Moderate | C3-R9 | useSyncKofiaDisclosures 무효화 범위 과다 |
| 🟡 Moderate | C3-Q1 | useRemoveFromWatchlist 테스트에서 alerts 무효화 미검증 |
| 🔵 Minor | C3-R4 | **실제 버그**: 뉴스 수집 onSuccess 타입 불일치 → `collected_count` 항상 undefined |
| 🔵 Minor | C3-R2 | useMarkAlertRead 이중 무효화 중복 |
| 🔵 Minor | C3-R3 | useCollectNews 센티먼트 처리 피드백 부재 |
| 🔵 Minor | C3-R5 | useNews용 MSW 핸들러 부재 |
| 🔵 Minor | C3-R7 | useClassifySanctions corpCode 클로저 캡처 |
| 🔵 Minor | C3-R8 | useSyncDartDisclosures mutation corpCode 미검증 |

---

### C4. KIIS 페이지 — 대시보드 & 기업 상세

**파일**: DashboardPage.tsx, CompanyDetailPage.tsx, CompanyFinancials.tsx, SentimentIndicator.tsx, dashboard.ts

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | C4-R4 | CompanyDetailPage `corpCode` undefined 시 early return 없음 → 잘못된 URL 생성 |
| 🟠 Major | C4-R9 | SentimentIndicator ARIA 속성 전무 — 스크린 리더 미지원 |
| 🟡 Moderate | C4-R1 | DashboardPage RecentDeal key 합성 — 매 렌더마다 새 배열 |
| 🟡 Moderate | C4-R6 | CompanyFinancials `keyField="account_nm"` — 중복 가능 |
| 🟡 Moderate | C4-R11 | useSyncDartDisclosures에 빈 문자열 방어 없음 |
| 🟡 Moderate | C4-R7 | CompanyFinancials 컬럼 헤더 "2 Years Ago" 하드코딩 |
| 🔵 Minor | C4-R8 | `currentYear` 모듈 로드 시 1회만 평가 |
| 🔵 Minor | C4-R10 | SentimentIndicator score 범위 제약 없음 |
| 🔵 Minor | C4-R12 | DashboardPage KPI 한국어 문자열 매칭 |
| 🔵 Minor | C4-R13 | formatDate 가드 스타일 불일치 |

---

### C5. KIIS 페이지 — 리스트 페이지들

**파일**: CompanyListPage.tsx, NewsListPage.tsx, WatchlistPage.tsx, FundListPage.tsx, ReitListPage.tsx

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | C5-R6 | **실제 버그**: NewsListPage `collected_count` 타입 불일치 → toast 항상 폴백 |
| 🟡 Moderate | C5-R1 | NewsListPage aria-label 중복 (보이는 제목과 동일) |
| 🟡 Moderate | C5-R4 | WatchlistPage columns `useMemo` 미적용 — 매 렌더마다 재생성 |
| 🔵 Minor | C5-R3 | WatchlistPage Pagination 조건 중복 적용 |
| 🔵 Minor | C5-R5 | CompanyList/FundList 검색 입력에 debounce 없음 |
| 🔵 Minor | C5-R7 | 워치리스트 전체 아이템 한번에 fetch (pagination 없음) |
| 🔵 Minor | C5-R8 | ReitListPage 텍스트 검색 기능 없음 |

---

### C6. KIIS 라우트 & 번들 최적화

**파일**: KiisRoutes.tsx, variants.ts, 타입 파일 7개 (헤더)

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟠 Major | C6-P1 | **KiisRoutes 18개 페이지 전량 정적 import** — FDD(5개)/IM(6개) 대비 3~3.6배, `/kiis` 진입 시 전부 다운로드 |
| 🟡 Moderate | C6-P2 | GallerySamplePage에 DEV 가드 없음 — 프로덕션 번들 포함 |
| 🔵 Minor | C6-P3 | `AlertType` dead type — 정의만 되고 사용처 없음 |
| 🔵 Minor | C6-P4 | `sanction.ts` severity union 미적용 |

---

### D2. IM 페이지 & 컴포넌트

**파일**: CreateDocumentPage.tsx, DocumentDetailPage.tsx, DocumentListPage.tsx, ProgressTracker.tsx, DocumentStatusBadge.tsx, ImErrorBoundary.tsx
**허위 발견 거부**: 4건 (25%) — cleanup 존재, getFailedStageIndex 정상, Badge variant 정상, class component 합당

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟡 Moderate | D2-R3 | CreateDocumentPage fetch 로직 중복 (useEffect vs handleFetchCompany) |
| 🟡 Moderate | D2-R7 | DocumentListPage KPI Total=서버 전체, 나머지=현재 페이지 기준 → 불일치 |
| 🟡 Moderate | D2-R9 | ProgressTracker NaN 방어 — 텍스트/progress bar에 미적용 (`"NaN%"` 가능) |
| 🔵 Minor | D2-R1 | 산업 자동매핑 useEffect dependency array `updateField` 누락 |
| 🔵 Minor | D2-R2 | handleSubmit에 mountedRef 가드 없음 |
| 🔵 Minor | D2-R4 | PDF 비밀번호 4자 최소 검증 — UI disabled에만 존재, submit 검증 없음 |
| 🔵 Minor | D2-R5 | handleRegenerate에 mountedRef 미적용 |
| 🔵 Minor | D2-R6 | FAILED 상태에서 백엔드 에러 메시지 미표시 |
| 🔵 Minor | D2-R8 | 상태 필터 클라이언트 측에서만 동작 — 서버 페이지네이션과 불일치 |
| 🔵 Minor | D2-R10 | ImErrorBoundary class component (합당한 예외이나 문서 보완 필요) |
| 🔵 Minor | D2-R11 | "Try Again"만 존재 — 반복 에러 시 네비게이션 버튼 없음 |
| 🔵 Minor | D2-R12 | Sentry 초기화 전 호출 시 동작 확인 필요 |

---

### D3. IM ↔ FDD 크로스모듈 통합

**파일**: industry.ts, im/document.ts, fdd/deal.ts, ImRoutes.tsx, BE deals.py, BE models.py

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🟡 Moderate | D3-F1 | FDD `deal.ts` `IndustryType` 중복 정의 (= B8-T1 동일) |
| 🔵 Minor | D3-F2 | BE-FE IndustryType 6개 현재 일치, 구조적 리스크만 존재 |
| 🔵 Minor | D3-F3 | Deal Summary API 3개 순차 쿼리 조회 |
| 🔵 Minor | D3-F6 | ImRoutes 내부 6개 페이지 eager import (SamplePage DEV 가드 있으나 import는 포함) |

**정상 확인**: IM document.ts IndustryId re-export 패턴 정상, FDD industry non-nullable vs IM nullable 의도적 차이

---

### F2. FDD DB & 트랜잭션

**파일**: database.py, models/deal.py, models/qoe.py, api/deals.py, api/qoe.py

| 심각도 | ID | 이슈 |
|--------|----|------|
| 🔴 High | F2-5.3 | `get_deal_summary`에서 `QoEStatus.COMPLETED` 참조 → enum에 없음 → **500 에러** (APPROVED로 변경 필요) |
| 🔴 Medium-High | F2-2.1 | `create_definition` 버전 번호 race condition — SELECT FOR UPDATE 없음, UNIQUE 제약 없음 |
| 🟡 Moderate | F2-1.2 | `deal_snapshot.definition_version_id` 인덱스 없음 |
| 🔵 Minor | F2-1.3 | `entity_id` FK 5개 테이블 인덱스 누락 |
| 🔵 Minor | F2-1.1 | `deal.team_partner_id`/`team_manager_id` 인덱스 없음 |
| 🔵 Minor | F2-4.2 | `pool_timeout` 미설정 (기본 30초) |
| 🔵 Minor | F2-5.1 | `get_db()` 명시적 rollback 없음 (암묵적 의존) |
| 🔵 Minor | F2-5.2 | 서비스 내부 commit — 트랜잭션 묶기 불가 |

**허위 발견 재확인**: ✅ setattr 화이트리스트 정상 (19개 필드 + Pydantic 이중 방어)

---

## 크로스커팅 패턴 분석

### 1. corpCode 검증 불일치 (KIIS 모듈 전체)

| 검증 O | 검증 X (!!corpCode만) |
|---------|----------------------|
| useDisclosures, usePortfolio | useCompanies (4개 함수), useDeals, useManagers, useSanctions |

**권장**: `CORP_CODE_RE = /^\d{8}$/` 검증을 모든 corpCode URL 삽입 지점에 일관 적용

### 2. 번들 크기 — React.lazy 미적용

| 모듈 | 페이지 수 | React.lazy |
|------|-----------|------------|
| FDD | 16 | ❌ 내부 정적 |
| KIIS | 18 | ❌ 내부 정적 |
| IM | 6 | ❌ 내부 정적 |

**참고**: 모듈 자체는 App.tsx에서 React.lazy로 로드되지만, 모듈 진입 시 모든 하위 페이지가 한 번에 번들됨. KIIS가 18개로 가장 심각.

### 3. Validation 부재 패턴

- FDD Deal 생성: 모달/위자드 모두 클라이언트 validation 불완전
- 파일 업로드: 확장자만 체크, 크기 제한 없음
- mutation에서 corpCode: 쿼리 훅은 검증하지만 mutation은 검증 없음

### 4. 다운로드 인증 패턴

- ReportVersionCard: `window.open()` → JWT 미전달 (B3-R11 = B7-A1)
- 수정안: Blob 다운로드 패턴 (ReportPage.tsx에 이미 구현됨)

---

## 우선순위별 수정 로드맵

### P0: 즉시 수정 (버그/크래시)

1. **F2-5.3**: `QoEStatus.COMPLETED` → `QoEStatus.APPROVED` (BE, 1줄 x 3곳)
2. **C5-R6 / C3-R4**: NewsListPage `collected_count` 타입 수정 (FE, 1곳)

### P1: 단기 수정 (1~2일)

3. **F2-2.1**: create_definition SELECT FOR UPDATE + UNIQUE 제약 추가
4. **B4-R1~R3**: DealListPage/DealSetupWizard validation 강화
5. **C1-A1**: KIIS corpCode 검증 일관화 (8개 함수)
6. **B3-R11 / B7-A1**: 다운로드 Blob 방식 전환

### P2: 중기 개선 (스프린트 내)

7. **C6-P1**: KiisRoutes React.lazy 전환 (18개 페이지)
8. **B8-T1 / D3-F1**: FDD deal.ts IndustryType → 공유 IndustryId 통합
9. **B7-R1**: 리포트 생성 후 캐시 무효화 추가
10. **B7-R2 / B3-R9**: 버전 목록 정렬 로직 추가
11. **C3-R1**: useAddToWatchlist alerts 무효화 추가

### P3: 장기 개선

12. Breadcrumbs 일괄 적용 (FDD 4개 페이지)
13. 접근성 보강 (SentimentIndicator, VDR ARIA, ReportPage fieldset)
14. 테스트 보강 (useUpdateDeal, 에러 케이스, MSW 핸들러)
15. staleTime 전역 전략 수립
