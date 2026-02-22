# AMIC x PETRA Platform — 코드 리뷰 프롬프트 모음

> 생성일: 2026-02-13 09:06
> 용도: 각 세션에서 복사하여 사용할 모듈별 코드 리뷰 프롬프트
> 순서: 세션 1(Platform) → 2(FDD) → 3(KIIS) → 4(IM) → 5(통합)

---

## 세션 1: Platform 공통 레이어 리뷰

```
Platform 공통 레이어(shared components, hooks, API, routing)를 꼼꼼하게 코드 리뷰해줘.
실제 앱이 원활하게 작동하는 것이 목표야.

## 리뷰 대상 파일

### API Client & 네트워크
- src/api/client.ts (createApiClient 팩토리)
- src/api/fddClient.ts, imClient.ts, kiisClient.ts

### 인증 & 권한
- src/hooks/useAuth.ts
- src/components/auth/AuthContext.ts
- src/components/auth/AuthProvider.tsx
- src/components/auth/ProtectedRoute.tsx
- src/types/auth.ts

### 레이아웃 & 네비게이션
- src/components/layout/AppShell.tsx
- src/components/layout/Sidebar.tsx
- src/components/layout/ModuleSwitcher.tsx
- src/components/layout/PageHeader.tsx
- src/components/layout/HealthIndicator.tsx

### UI 컴포넌트 라이브러리
- src/components/ui/ 전체 (Badge, Button, Card, DataTable, Input, Modal,
  Select, Pagination, KpiCard, EmptyState, Skeleton, Spinner 등)

### 포탈 기능 Hooks
- src/hooks/useAnalytics.ts, useDashboard.ts, useGlobalSearch.ts
- src/hooks/useFavorites.ts, useNotifications.ts, useExports.ts
- src/hooks/useCalendar.ts, useComments.ts, useTeamMembers.ts
- src/hooks/useHealthCheck.ts, useIntegrations.ts, usePreferences.ts

### 포탈 페이지
- src/pages/DashboardPage.tsx, LoginPage.tsx
- src/pages/admin/UserManagementPage.tsx, ActivityLogPage.tsx
- src/pages/analytics/AnalyticsPage.tsx
- src/pages/calendar/CalendarPage.tsx
- src/pages/exports/ExportsPage.tsx
- src/pages/help/HelpPage.tsx
- src/pages/settings/ProfilePage.tsx, WebhooksPage.tsx

### 유틸리티
- src/lib/format.ts, cn.ts, storage.ts, statusVariant.ts
- src/lib/sentry.ts, ics.ts

### 라우팅 & 진입점
- src/main.tsx, src/App.tsx
- vite.config.ts (프록시 설정)

## 점검 관점

1. **런타임 버그**
   - createApiClient의 인터셉터: 토큰 갱신 실패 시 무한 루프 가능성
   - AuthProvider 초기화: race condition, 토큰 만료 시 리다이렉트 로직
   - React.lazy 동적 import 실패 시 fallback 처리
   - useHealthCheck 폴링: 컴포넌트 언마운트 후 setState 호출 여부

2. **타입 안전성**
   - API 응답 타입: as 단언 없이 런타임 검증하는지
   - UI 컴포넌트 props: 필수/선택 구분, 제네릭 타입 정확성
   - React Query 키 팩토리: 타입 일관성

3. **API 연동**
   - Vite 프록시 설정과 실제 API 호출 경로 일치 여부
   - 각 모듈 클라이언트(fdd/kiis/im)의 baseURL 정확성
   - 에러 응답 처리: 401, 403, 404, 500 각각 적절히 처리되는지
   - 요청 취소(AbortController) 구현 여부

4. **상태 관리**
   - React Query staleTime/cacheTime 설정 적절성
   - 인증 상태와 쿼리 캐시 동기화 (로그아웃 시 캐시 클리어)
   - 전역 상태 vs 서버 상태 구분 적절성

5. **UX 결함**
   - 모든 페이지: 로딩/에러/빈 상태 3가지 처리 확인
   - Sidebar 반응형: 모바일 메뉴 토글 동작
   - CommandPalette(Ctrl+K): 포커스 트래핑, ESC 닫기
   - 접근성: aria 속성, 키보드 네비게이션

6. **보안**
   - 토큰 저장 방식 (localStorage vs httpOnly cookie)
   - XSS: dangerouslySetInnerHTML 사용 여부
   - CORS 설정 적절성

## 출력 형식

각 이슈를 아래 형식으로 정리:
- **파일**: 경로:라인번호
- **심각도**: Critical / Major / Minor
- **문제**: 구체적으로 무엇이 잘못됐는지
- **수정안**: 코드 변경 제안 (diff 형식 선호)

심각도별로 그룹핑하고, Critical → Major → Minor 순서로 정렬해줘.
리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 2: FDD 모듈 리뷰

```
FDD(Financial Due Diligence) 모듈 프론트엔드를 꼼꼼하게 코드 리뷰해줘.
백엔드 API 스펙과의 정합성도 함께 검증해야 해.

## 리뷰 대상 — 프론트엔드

### 페이지 (16개)
- src/modules/fdd/pages/DealListPage.tsx — 딜 목록, 필터링, 정렬
- src/modules/fdd/pages/DealSetupPage.tsx — 딜 생성
- src/modules/fdd/pages/DealSetupWizardPage.tsx — 딜 생성 위자드
- src/modules/fdd/pages/DealWorkspacePage.tsx — 딜 워크스페이스 (탭 라우팅)
- src/modules/fdd/pages/UploadPage.tsx — 파일 업로드
- src/modules/fdd/pages/DefinitionPage.tsx — 계정 정의
- src/modules/fdd/pages/MappingPage.tsx — 계정 매핑
- src/modules/fdd/pages/QoEPage.tsx — Quality of Earnings 분석
- src/modules/fdd/pages/NWCPage.tsx — Net Working Capital 분석
- src/modules/fdd/pages/NetDebtPage.tsx — Net Debt 분석
- src/modules/fdd/pages/IssuesPage.tsx — 이슈 트래커
- src/modules/fdd/pages/ReportPage.tsx — 리포트
- src/modules/fdd/pages/VdrPage.tsx — Virtual Data Room
- src/modules/fdd/pages/WorkflowOverviewPage.tsx — 워크플로우 개요

### Hooks (9개)
- src/modules/fdd/hooks/useDeals.ts — 딜 CRUD + 목록
- src/modules/fdd/hooks/useUploads.ts — 파일 업로드/삭제
- src/modules/fdd/hooks/useMapping.ts — 계정 매핑
- src/modules/fdd/hooks/useQoE.ts — QoE 데이터 조회/수정
- src/modules/fdd/hooks/useNWC.ts — NWC 데이터
- src/modules/fdd/hooks/useDebt.ts — Debt 데이터
- src/modules/fdd/hooks/useIssues.ts — 이슈 CRUD
- src/modules/fdd/hooks/useReportVersions.ts — 리포트 버전 관리
- src/modules/fdd/hooks/useVdr.ts — VDR 폴더/파일

### 컴포넌트 (6개)
- src/modules/fdd/components/deal/DealSetupWizard.tsx — 멀티스텝 폼
- src/modules/fdd/components/deal/ScopeSelector.tsx — 분석 범위 선택
- src/modules/fdd/components/report/ReportVersionCard.tsx
- src/modules/fdd/components/report/ReportVersionList.tsx
- src/modules/fdd/components/vdr/VdrFolderItem.tsx
- src/modules/fdd/components/vdr/VdrFolderTree.tsx

### 타입 (9개)
- src/modules/fdd/types/deal.ts, debt.ts, evidence.ts, issue.ts
- src/modules/fdd/types/mapping.ts, nwc.ts, qoe.ts
- src/modules/fdd/types/report-version.ts, vdr.ts

### 라우팅
- src/modules/fdd/FddRoutes.tsx

## 리뷰 대상 — 백엔드 (API 정합성 검증용)

아래 백엔드 파일들을 참조하여 프론트엔드 타입/API 호출이 정확한지 검증해줘:

- Auto FDD/backend/app/api/deals.py — 딜 API 엔드포인트
- Auto FDD/backend/app/api/uploads.py — 업로드 API
- Auto FDD/backend/app/api/mapping.py — 매핑 API
- Auto FDD/backend/app/api/qoe.py — QoE API
- Auto FDD/backend/app/api/nwc.py — NWC API
- Auto FDD/backend/app/api/debt.py — Debt API
- Auto FDD/backend/app/api/issues.py — 이슈 API
- Auto FDD/backend/app/api/reports.py — 리포트 API
- Auto FDD/backend/app/api/vdr.py — VDR API
- Auto FDD/backend/app/api/industries.py — 산업 API

- Auto FDD/backend/app/schemas/deal.py — 딜 DTO
- Auto FDD/backend/app/schemas/upload.py — 업로드 DTO
- Auto FDD/backend/app/schemas/mapping.py — 매핑 DTO
- Auto FDD/backend/app/schemas/qoe.py — QoE DTO
- Auto FDD/backend/app/schemas/nwc.py — NWC DTO
- Auto FDD/backend/app/schemas/debt.py — Debt DTO
- Auto FDD/backend/app/schemas/issue.py — 이슈 DTO
- Auto FDD/backend/app/schemas/report_version.py — 리포트 DTO
- Auto FDD/backend/app/schemas/vdr.py — VDR DTO

## 점검 관점

1. **프론트엔드 ↔ 백엔드 타입 불일치**
   - FE 타입 정의(types/*.ts) vs BE 스키마(schemas/*.py) 필드명/타입 비교
   - API 호출 URL 경로가 백엔드 라우터와 일치하는지
   - 요청 body/params 구조 일치 여부
   - 응답 페이지네이션 형식 일치 여부
   - enum 값(status, industry 등) 양쪽 일치 여부

2. **런타임 버그**
   - DealSetupWizard 멀티스텝 폼: 단계 간 상태 유지, 뒤로가기 시 데이터 보존
   - 파일 업로드: 대용량 파일 처리, 진행률 표시, 실패 시 재시도
   - QoE/NWC/Debt 페이지: 데이터 로딩 경쟁 조건, 빈 데이터 처리
   - VDR 트리 컴포넌트: 재귀 렌더링 성능, 깊은 중첩 처리
   - Industry 선택: 기본값 처리, 미선택 시 동작

3. **상태 관리**
   - React Query 키 구조: dealId 기반 쿼리 무효화 정확성
   - 낙관적 업데이트(optimistic update) 실패 시 롤백 처리
   - 딜 상태 전이: 워크플로우 단계별 데이터 의존성

4. **UX**
   - 각 페이지별 로딩/에러/빈 상태 처리 누락 여부
   - 폼 유효성 검증: 필수 필드, 형식 검증
   - 워크플로우 네비게이션: 이전/다음 단계 이동 로직

## 출력 형식

각 이슈를 아래 형식으로 정리:
- **파일**: 경로:라인번호
- **심각도**: Critical / Major / Minor
- **카테고리**: 타입불일치 | 런타임버그 | 상태관리 | UX결함
- **문제**: 구체적으로 무엇이 잘못됐는지
- **수정안**: 코드 변경 제안

기존 리뷰 참고: docs/20260213_0833_FDD_Code_Review.md
(이미 발견된 이슈는 제외하고, 새로운 이슈만 보고)
리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 3: KIIS 모듈 리뷰

```
KIIS(핵심투자정보조사서) 모듈 프론트엔드를 꼼꼼하게 코드 리뷰해줘.
백엔드 API 스펙과의 정합성도 함께 검증해야 해.

## 리뷰 대상 — 프론트엔드

### 페이지 (18개)
- src/modules/kiis/pages/DashboardPage.tsx — 대시보드 (KPI, 차트)
- src/modules/kiis/pages/CompanyListPage.tsx — 기업 목록
- src/modules/kiis/pages/CompanyDetailPage.tsx — 기업 상세 (재무, 뉴스, 제재)
- src/modules/kiis/pages/NewsListPage.tsx — 뉴스 목록
- src/modules/kiis/pages/NewsDetailPage.tsx — 뉴스 상세
- src/modules/kiis/pages/WatchlistPage.tsx — 관심기업 목록
- src/modules/kiis/pages/SanctionListPage.tsx — 제재 목록
- src/modules/kiis/pages/FundListPage.tsx — 펀드 목록
- src/modules/kiis/pages/FundDetailPage.tsx — 펀드 상세
- src/modules/kiis/pages/ReitListPage.tsx — 리츠 목록
- src/modules/kiis/pages/ReitDetailPage.tsx — 리츠 상세
- src/modules/kiis/pages/ManagerListPage.tsx — 운용사 목록
- src/modules/kiis/pages/ManagerProfilePage.tsx — 운용사 프로필
- src/modules/kiis/pages/PortfolioPage.tsx — 포트폴리오
- src/modules/kiis/pages/DealSourcingPage.tsx — 딜 소싱
- src/modules/kiis/pages/DisclosurePage.tsx — 공시 정보
- src/modules/kiis/pages/EntityResolutionPage.tsx — 엔티티 해소

### Hooks (14개)
- src/modules/kiis/hooks/useCompanies.ts — 기업 CRUD + 검색
- src/modules/kiis/hooks/useDashboard.ts — 대시보드 데이터
- src/modules/kiis/hooks/useNews.ts — 뉴스 목록/상세
- src/modules/kiis/hooks/useWatchlist.ts — 관심기업 관리
- src/modules/kiis/hooks/useSanctions.ts — 제재 조회
- src/modules/kiis/hooks/useFunds.ts — 펀드 데이터
- src/modules/kiis/hooks/useReits.ts — 리츠 데이터
- src/modules/kiis/hooks/useManagers.ts — 운용사 데이터
- src/modules/kiis/hooks/usePortfolio.ts — 포트폴리오
- src/modules/kiis/hooks/useDeals.ts — 딜 소싱
- src/modules/kiis/hooks/useDisclosures.ts — 공시
- src/modules/kiis/hooks/useEntities.ts — 엔티티 해소
- src/modules/kiis/hooks/useAnalysis.ts — 분석 결과
- src/modules/kiis/hooks/useSearch.ts — 통합 검색

### 컴포넌트 (8개)
- src/modules/kiis/components/SearchBar.tsx — 검색 바
- src/modules/kiis/components/CompanyFinancials.tsx — 재무 테이블/차트
- src/modules/kiis/components/SentimentIndicator.tsx — 감성 지표
- src/modules/kiis/components/ReputationBadge.tsx — 평판 뱃지
- src/modules/kiis/components/DealTrendChart.tsx — 딜 트렌드 차트
- src/modules/kiis/components/ValuationModal.tsx — 밸류에이션 모달
- src/modules/kiis/components/CorpCodeInput.tsx — 법인코드 입력
- src/modules/kiis/components/AliasCreateForm.tsx — 별칭 등록 폼

### 타입 (14개)
- src/modules/kiis/types/company.ts, dashboard.ts, news.ts, watchlist.ts
- src/modules/kiis/types/sanction.ts, fund.ts, reit.ts, manager.ts
- src/modules/kiis/types/portfolio.ts, deal.ts, disclosure.ts, entity.ts
- src/modules/kiis/types/analysis.ts, search.ts

### 상수 & 라우팅
- src/modules/kiis/constants/variants.ts
- src/modules/kiis/KiisRoutes.tsx

## 리뷰 대상 — 백엔드 (API 정합성 검증용)

KIIS 백엔드 파일을 참조하여 프론트엔드와의 정합성 검증:

### 라우터 (대응하는 FE 훅과 비교)
- KIIS/app/routers/company.py ↔ useCompanies.ts
- KIIS/app/routers/dashboard.py ↔ useDashboard.ts
- KIIS/app/routers/news.py ↔ useNews.ts
- KIIS/app/routers/sanctions.py ↔ useSanctions.ts
- KIIS/app/routers/deals.py ↔ useDeals.ts
- KIIS/app/routers/portfolio.py ↔ usePortfolio.ts
- KIIS/app/routers/managers.py ↔ useManagers.ts
- KIIS/app/routers/disclosures.py ↔ useDisclosures.ts
- KIIS/app/routers/entity.py ↔ useEntities.ts
- KIIS/app/routers/search.py ↔ useSearch.ts
- KIIS/app/routers/analysis.py ↔ useAnalysis.ts
- KIIS/app/routers/reits.py ↔ useReits.ts
- KIIS/app/routers/kofia.py ↔ useFunds.ts

### 스키마 (대응하는 FE 타입과 비교)
- KIIS/app/schemas/company.py ↔ types/company.ts
- KIIS/app/schemas/dashboard.py ↔ types/dashboard.ts
- KIIS/app/schemas/news.py ↔ types/news.ts
- KIIS/app/schemas/sanction.py ↔ types/sanction.ts
- KIIS/app/schemas/deal.py ↔ types/deal.ts
- KIIS/app/schemas/portfolio.py ↔ types/portfolio.ts
- KIIS/app/schemas/manager.py ↔ types/manager.ts
- KIIS/app/schemas/disclosure.py ↔ types/disclosure.ts
- KIIS/app/schemas/entity.py ↔ types/entity.ts
- KIIS/app/schemas/search.py ↔ types/search.ts
- KIIS/app/schemas/analysis.py ↔ types/analysis.ts
- KIIS/app/schemas/reits.py ↔ types/reit.ts
- KIIS/app/schemas/fund.py ↔ types/fund.ts (존재 여부 확인)

## 점검 관점

1. **프론트엔드 ↔ 백엔드 타입 불일치**
   - 14개 타입 파일 각각을 대응하는 백엔드 스키마와 필드 단위로 비교
   - API 경로(URL path)가 백엔드 라우터 prefix와 일치하는지
   - 페이지네이션 파라미터(skip/limit vs page/size) 일치 여부
   - 날짜 형식(ISO string vs timestamp) 일관성
   - 선택적/필수 필드 불일치

2. **런타임 버그**
   - CompanyDetailPage: 여러 탭(재무/뉴스/제재) 동시 로딩 시 경쟁 조건
   - WatchlistPage: 관심기업 추가/삭제 후 목록 갱신 누락 가능성
   - SearchBar: 디바운싱 구현, 빈 검색어 처리
   - CompanyFinancials: 재무 데이터 없는 기업 처리
   - SentimentIndicator: 감성 점수 범위 벗어난 값 처리
   - FundDetailPage/ReitDetailPage: 존재하지 않는 ID 접근 시 처리
   - EntityResolutionPage: 엔티티 병합 동작 후 관련 데이터 무효화

3. **상태 관리**
   - 14개 훅의 React Query 키 구조: 충돌 가능성
   - 관련 데이터 간 캐시 무효화 (예: 기업 수정 → 관심목록 갱신)
   - 검색 결과 캐싱 전략

4. **UX**
   - 18개 페이지 각각: 로딩/에러/빈 상태 처리 확인
   - ValuationModal: 폼 유효성 검증, 저장 중 중복 클릭 방지
   - CorpCodeInput: 유효한 법인코드 형식 검증
   - 리스트 페이지들: 페이지네이션, 정렬, 필터 동작

## 출력 형식

각 이슈를 아래 형식으로 정리:
- **파일**: 경로:라인번호
- **심각도**: Critical / Major / Minor
- **카테고리**: 타입불일치 | 런타임버그 | 상태관리 | UX결함
- **문제**: 구체적으로 무엇이 잘못됐는지
- **수정안**: 코드 변경 제안

기존 리뷰 참고: docs/20260213_0836_KIIS_Code_Review.md
(이미 발견된 이슈는 제외하고, 새로운 이슈만 보고)
리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 4: IM 모듈 리뷰

```
IM(Information Memorandum) Generator 모듈 프론트엔드를 꼼꼼하게 코드 리뷰해줘.
백엔드 API 스펙과의 정합성도 함께 검증해야 해.

## 리뷰 대상 — 프론트엔드

### 페이지 (6개)
- src/modules/im/pages/DocumentListPage.tsx — 문서 목록, 상태 필터
- src/modules/im/pages/CreateDocumentPage.tsx — 문서 생성 폼 (기업 선택, 산업 선택)
- src/modules/im/pages/DocumentDetailPage.tsx — 문서 상세 (섹션별 진행, 다운로드)
- src/modules/im/pages/TemplatesPage.tsx — 템플릿 관리

### Hooks (2개)
- src/modules/im/hooks/useDocuments.ts — 문서 CRUD, 생성 요청, 상태 폴링
- src/modules/im/hooks/useCompanies.ts — 기업 검색/조회

### 컴포넌트 (3개)
- src/modules/im/components/DocumentStatusBadge.tsx — 상태 뱃지
- src/modules/im/components/ImErrorBoundary.tsx — IM 전용 에러 바운더리
- src/modules/im/components/ProgressTracker.tsx — 생성 진행률 트래커

### 타입 (2개)
- src/modules/im/types/document.ts — 문서 타입 (IndustryId re-export 포함)
- src/modules/im/types/company.ts — 기업 타입

### 공유 타입
- src/types/industry.ts — IndustryId, FDD_INDUSTRY_OPTIONS (FDD ↔ IM 공유)

### 라우팅
- src/modules/im/ImRoutes.tsx

## 리뷰 대상 — 백엔드 (API 정합성 검증용)

IM 백엔드 파일을 참조하여 프론트엔드와의 정합성 검증:

### API 라우트
- IM Module/auto-im-generator/src/api/routes/documents.py ↔ useDocuments.ts
- IM Module/auto-im-generator/src/api/routes/companies.py ↔ useCompanies.ts
- IM Module/auto-im-generator/src/api/routes/health.py

### 스키마
- IM Module/auto-im-generator/src/api/schemas/documents.py ↔ types/document.ts
- IM Module/auto-im-generator/src/api/schemas/companies.py ↔ types/company.ts

### 비동기 작업 (프론트엔드 폴링과 연관)
- IM Module/auto-im-generator/src/api/tasks/generate_im.py — 문서 생성 태스크
- IM Module/auto-im-generator/src/api/tasks/progress.py — 진행률 보고

## 점검 관점

1. **프론트엔드 ↔ 백엔드 타입 불일치**
   - Document 타입: status enum 값 양쪽 일치 여부
   - Company 타입: 검색 API 응답 구조 일치
   - IndustryId: 프론트엔드(9 values) vs 백엔드 지원 산업 목록 일치
   - 문서 생성 요청 body: 필수 필드, 선택 필드 정확성
   - 진행률 API: 폴링 응답 구조, 섹션별 상태 필드

2. **런타임 버그**
   - CreateDocumentPage: 기업 검색 → 선택 → 산업 자동 설정 흐름
   - DocumentDetailPage: 생성 중 문서의 실시간 진행률 폴링
     → 폴링 간격, 완료 감지, 에러 시 중단 로직
     → 컴포넌트 언마운트 시 폴링 정리
   - ProgressTracker: 진행률 100% 도달 후 상태 전환
   - DocumentStatusBadge: 모든 상태값에 대한 뱃지 매핑 누락 여부
   - ImErrorBoundary: 에러 복구(retry) 동작

3. **FDD ↔ IM 크로스 모듈 통합**
   - IndustryId 공유: import 경로 정확성
   - FDD deal summary → IM 문서 생성 연동 가능성 검증

4. **UX**
   - CreateDocumentPage: 폼 유효성, 중복 제출 방지
   - DocumentListPage: 상태별 필터, 정렬, 페이지네이션
   - DocumentDetailPage: 생성 완료 후 다운로드 링크
   - TemplatesPage: 템플릿 목록 로딩/빈 상태

5. **기존 감사 결과 검증**
   - docs/20260212_1659_IM_FE_BE_Mismatch_Audit.md에서 발견된 이슈가
     코드에 반영되었는지 확인

## 출력 형식

각 이슈를 아래 형식으로 정리:
- **파일**: 경로:라인번호
- **심각도**: Critical / Major / Minor
- **카테고리**: 타입불일치 | 런타임버그 | 크로스모듈 | UX결함
- **문제**: 구체적으로 무엇이 잘못됐는지
- **수정안**: 코드 변경 제안

기존 감사 참고: docs/20260212_1659_IM_FE_BE_Mismatch_Audit.md
리뷰 결과를 docs/ 폴더에 저장해줘.
```

---

## 세션 5: 크로스 모듈 통합 리뷰

```
개별 모듈 리뷰가 완료되었어. 이제 크로스 모듈 관점에서 통합 리뷰해줘.

## 리뷰 대상

### 기존 리뷰 문서 (필수 읽기)
- docs/20260213_0833_FDD_Code_Review.md
- docs/20260213_0836_KIIS_Code_Review.md
- docs/20260212_1659_IM_FE_BE_Mismatch_Audit.md
- (세션 1~4에서 생성된 추가 리뷰 문서들)

### 모듈 간 공유 지점
- src/api/client.ts — 3개 모듈 공통 API 팩토리
- src/api/fddClient.ts, kiisClient.ts, imClient.ts — 각 모듈 클라이언트
- src/types/industry.ts — FDD ↔ IM 공유 타입
- src/components/auth/ — 인증 (3개 모듈 공통)
- src/components/ui/ — UI 라이브러리 (3개 모듈 공통)
- src/hooks/useAuth.ts — 인증 훅 (3개 모듈 공통)
- vite.config.ts — 프록시 설정 (/api/fdd, /api/kiis, /api/im)

### 라우팅 통합
- src/main.tsx — 앱 진입점
- src/modules/fdd/FddRoutes.tsx
- src/modules/kiis/KiisRoutes.tsx
- src/modules/im/ImRoutes.tsx

## 점검 관점

1. **모듈 간 패턴 일관성**
   - 3개 모듈의 hook 패턴 비교: React Query 키 네이밍, 에러 처리,
     캐시 설정이 동일한 패턴을 따르는지
   - 3개 모듈의 페이지 패턴 비교: 로딩/에러/빈 상태 처리 방식 통일
   - 타입 정의 패턴: Paginated 응답, 에러 응답 등 공통 패턴 일치

2. **API 클라이언트 일관성**
   - 3개 모듈 클라이언트의 인터셉터 설정 동일 여부
   - 에러 핸들링: 401 → 로그아웃, 403 → 권한 없음 처리 통일
   - baseURL 설정과 Vite 프록시 경로 정합성

3. **라우팅 & 네비게이션**
   - 모듈 간 이동 시 상태 유지/초기화 정책
   - 딥링크: /fdd/deals/:id, /kiis/companies/:id, /im/documents/:id
   - 404 처리: 존재하지 않는 경로, 존재하지 않는 리소스 ID
   - Lazy loading: 각 모듈 청크 분리 정상 동작

4. **FDD ↔ IM 통합**
   - IndustryId 타입 공유 경로 및 import 정확성
   - FDD deal summary → IM 문서 생성 데이터 흐름
   - 산업 옵션 목록(FDD_INDUSTRY_OPTIONS) 양쪽 일치

5. **성능 & 번들**
   - 모듈별 코드 스플리팅 정상 동작
   - 공유 라이브러리(recharts 등) 중복 번들링 여부
   - React Query devtools 프로덕션 제거 여부

6. **보안 통합**
   - 인증 토큰이 3개 백엔드 모두에 올바르게 전달되는지
   - 로그아웃 시 3개 모듈 캐시 모두 클리어되는지
   - CORS: 3개 백엔드의 origin 설정 일관성

## 출력 형식

이슈를 크로스 모듈 관점에서 분류:
- **영향 범위**: 어떤 모듈들이 영향받는지 (FDD+IM, 전체 등)
- **심각도**: Critical / Major / Minor
- **문제**: 구체적 설명
- **수정안**: 어디서 무엇을 변경해야 하는지

최종 결과를 docs/ 폴더에 통합 리뷰 문서로 저장해줘.
```

---

## 사용 가이드

| 세션 | 범위 | 예상 파일 수 | 순서 |
|------|------|-------------|------|
| 1 | Platform 공통 | ~100 파일 | 먼저 (기반) |
| 2 | FDD 모듈 | FE 38 + BE 참조 | 2번째 |
| 3 | KIIS 모듈 | FE 46 + BE 참조 | 3번째 |
| 4 | IM 모듈 | FE 15 + BE 참조 | 4번째 |
| 5 | 크로스 모듈 통합 | 리뷰 문서 + 핵심 파일 | 마지막 |

### 사용법
1. 새 세션을 열고 해당 세션의 프롬프트를 복사하여 붙여넣기
2. 리뷰 결과 문서가 생성되면 다음 세션으로 진행
3. 세션 5(통합)에서는 세션 1~4의 리뷰 문서를 참조하므로 마지막에 실행
