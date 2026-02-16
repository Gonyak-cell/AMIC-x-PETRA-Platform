# 통합 투자 플랫폼 프론트엔드 구축 계획

## Context

AMIC Law 내부팀이 사용하는 3개 독립 프로젝트(Auto FDD, IM Module, KIIS)를 하나의 통합 프론트엔드 플랫폼으로 합친다. 현재 Auto FDD만 프론트엔드가 있고(React 19 + TS + Vite, ~85% 완성), IM Module과 KIIS는 백엔드만 존재한다. Auto FDD의 프론트엔드를 기반으로 확장하여 통합 플랫폼을 구축한다.

---

## 프론트엔드 평가 결과

| 항목 | IM Module_backup | Auto FDD_backup | KIIS_backup |
|------|-----------------|-----------------|-------------|
| **프론트엔드 존재** | 없음 (0%) | 있음 (~85-90%) | 없음 (0%) |
| **프레임워크** | - | React 19 + TypeScript + Vite 6 | - |
| **상태관리** | - | TanStack Query v5 | - |
| **스타일링** | - | Tailwind CSS 3.4 | - |
| **라우팅** | - | React Router v7 | - |
| **인증** | - | JWT + auto-refresh | - |
| **페이지 수** | - | 15개 페이지 (~4,600 lines) | - |
| **컴포넌트** | - | 25+ (UI 라이브러리 포함) | - |
| **차트** | - | Recharts (Waterfall, Bar, Trend) | - |
| **코드 품질** | - | ESLint strict, TS strict, no `any` | - |
| **배포** | - | Docker + Nginx 프로덕션 빌드 | - |
| **백엔드 API** | 계획만 (~23 티켓) | 17개 라우터 모듈 완비 | 16개 도메인, 20+ 엔드포인트 |

**결론: Auto FDD_backup이 유일하게 프론트엔드를 보유하며, 프로덕션 수준 품질**

---

## 아키텍처 결정

### 단일 React 앱 + 모듈 라우팅
- Auto FDD 프론트엔드를 그대로 확장 (새 프로젝트 생성 X)
- React Router v7의 중첩 라우팅으로 모듈 분리: `/fdd/*`, `/im/*`, `/kiis/*`
- `React.lazy()` + `Suspense`로 모듈별 코드 스플리팅

### 3 백엔드 → 1 Nginx 리버스 프록시
- 각 백엔드를 별도 서비스로 유지 (마이크로서비스)
- Nginx에서 경로 기반 라우팅:
  - `/api/fdd/*` → Auto FDD backend (port 8000)
  - `/api/im/*` → IM Module backend (port 8001)
  - `/api/kiis/*` → KIIS backend (port 8002)
- Vite dev proxy도 동일 패턴

### 통합 인증
- Auto FDD의 JWT 인증 시스템을 공유 인증 서비스로 승격
- 모든 백엔드가 동일 JWT secret으로 토큰 검증
- 프론트엔드는 단일 토큰으로 3개 백엔드 접근

---

## 디렉토리 구조 (Auto FDD frontend/ 기준 확장)

```
frontend/src/
├── api/
│   ├── client.ts              ← 수정: createApiClient() 팩토리 함수
│   ├── fddClient.ts           ← 새로: /api/fdd/v1 인스턴스
│   ├── imClient.ts            ← 새로: /api/im/v1 인스턴스
│   └── kiisClient.ts          ← 새로: /api/kiis/v1 인스턴스
├── components/
│   ├── auth/                  ← 재사용 (AuthProvider, ProtectedRoute)
│   ├── layout/
│   │   ├── AppShell.tsx       ← 재사용
│   │   ├── Sidebar.tsx        ← 수정: 모듈 스위처 + 동적 네비게이션
│   │   ├── ModuleSwitcher.tsx ← 새로: FDD/IM/KIIS 전환 드롭다운
│   │   └── PageHeader.tsx     ← 재사용
│   ├── ui/                    ← 전체 재사용 (14개 컴포넌트)
│   ├── charts/                ← 재사용 (Waterfall, Bar, Trend)
│   └── shared/                ← 새로: 모듈 간 공유 컴포넌트
│       ├── CompanySearch.tsx   ← 3모듈 공통 회사 검색
│       └── StatusTimeline.tsx  ← 작업 진행률 표시
├── modules/
│   ├── fdd/                   ← 기존 FDD 페이지들 이동
│   │   ├── pages/             ← 기존 15개 페이지 (수정 최소화)
│   │   ├── hooks/             ← 기존 11개 훅
│   │   └── types/             ← 기존 10개 타입 파일
│   ├── im/                    ← 새로: IM Module 프론트엔드
│   │   ├── pages/
│   │   │   ├── ImDashboardPage.tsx      ← IM 문서 목록 + KPI
│   │   │   ├── ImCreatePage.tsx         ← 문서 생성 위자드
│   │   │   ├── ImStatusPage.tsx         ← 파이프라인 진행률 추적
│   │   │   ├── ImPreviewPage.tsx        ← 생성된 문서 미리보기
│   │   │   └── ImCompanyPage.tsx        ← 회사 데이터 조회/캐시
│   │   ├── hooks/
│   │   │   ├── useDocuments.ts          ← 문서 CRUD
│   │   │   ├── useDocumentStatus.ts     ← 폴링/SSE 진행률
│   │   │   └── useImCompanies.ts        ← 회사 데이터
│   │   └── types/
│   │       └── im.ts                    ← ImDocument, Pipeline 등
│   └── kiis/                  ← 새로: KIIS 프론트엔드
│       ├── pages/
│       │   ├── KiisDashboardPage.tsx    ← 시스템 대시보드 + KPI
│       │   ├── CompanySearchPage.tsx    ← 기업 검색 + 상세
│       │   ├── CompanyDetailPage.tsx    ← 기업 재무/공시/뉴스
│       │   ├── NewsFeedPage.tsx         ← 뉴스 피드 + 감성분석
│       │   ├── DealPipelinePage.tsx     ← 딜 소싱 + 섹터별 트렌드
│       │   ├── PortfolioPage.tsx        ← 포트폴리오 모니터링
│       │   ├── WatchlistPage.tsx        ← 관심종목 + 알림
│       │   └── ReputationPage.tsx       ← 평판 스코어링
│       ├── hooks/
│       │   ├── useCompanies.ts
│       │   ├── useNews.ts
│       │   ├── useDeals.ts
│       │   ├── useDashboard.ts
│       │   ├── useWatchlist.ts
│       │   └── useReputation.ts
│       └── types/
│           └── kiis.ts
├── App.tsx                    ← 수정: 모듈별 lazy 라우팅
├── main.tsx                   ← 재사용
└── index.css                  ← 재사용
```

---

## 핵심 파일 수정 목록

### 1. Sidebar 리팩토링
**파일**: `frontend/src/components/layout/Sidebar.tsx`
- 상단에 ModuleSwitcher 추가 (FDD / IM / KIIS 전환)
- 네비게이션 아이템을 현재 모듈에 따라 동적 렌더링
- 네비게이션 config를 각 모듈에서 export하는 구조

### 2. App.tsx 라우팅 확장
**파일**: `frontend/src/App.tsx`
```
/login → LoginPage
/ → ModuleSwitcher (또는 통합 대시보드)
/fdd/* → React.lazy(() => import('./modules/fdd/FddRoutes'))
/im/* → React.lazy(() => import('./modules/im/ImRoutes'))
/kiis/* → React.lazy(() => import('./modules/kiis/KiisRoutes'))
```

### 3. API Client 팩토리화
**파일**: `frontend/src/api/client.ts`
- `createApiClient(baseURL)` 팩토리 함수로 리팩토링
- JWT 인터셉터 로직을 공유하되 baseURL만 다르게
- 각 모듈용 클라이언트 인스턴스 생성

### 4. Vite/Nginx 프록시 확장
**파일**: `frontend/vite.config.ts`, `frontend/nginx.conf`
- 3개 백엔드로의 프록시 경로 추가

---

## 구현 단계

### Phase 1: 플랫폼 기반 구축 (3-4일)
> 기존 FDD 기능을 깨뜨리지 않으면서 확장 가능한 구조로 리팩토링

1. **기존 pages/hooks/types를 `modules/fdd/`로 이동**
2. **Sidebar에 ModuleSwitcher 컴포넌트 추가**
3. **App.tsx를 모듈별 lazy 라우팅으로 변경**
4. **API client를 팩토리 패턴으로 리팩토링**
5. **Vite proxy 설정에 `/api/im`, `/api/kiis` 추가**
6. **기존 FDD 기능이 `/fdd/*` 경로에서 정상 동작 확인**

**병렬 가능**: 1+2를 병렬, 3+4를 병렬, 5는 독립

### Phase 2: IM Module 프론트엔드 (5-7일)
> IM Module의 API가 먼저 구축되어야 함 (현재 0%)
> API 구축과 프론트엔드를 병렬로 진행 가능 (mock API 사용)

1. **ImDashboardPage** — 문서 목록 테이블, 상태 필터, KPI 카드
2. **ImCreatePage** — 스텝 위자드 (회사선택 → 기간설정 → 템플릿선택 → 생성)
3. **ImStatusPage** — 파이프라인 5단계 진행률 (SSE/폴링), 로그 뷰
4. **ImPreviewPage** — 생성된 PPTX/PDF 미리보기 + 다운로드
5. **ImCompanyPage** — DART 기업 검색, 재무데이터 캐시 조회
6. **hooks + types** 작성

**병렬 가능**: 1+5를 병렬, 2+3를 병렬 (4는 3 이후)

### Phase 3: KIIS 프론트엔드 (7-10일)
> KIIS 백엔드는 ~80% 완성이므로 바로 연동 가능

1. **KiisDashboardPage** — 시스템 요약 KPI, 최근 뉴스, 활성 딜
2. **CompanySearchPage** — ElasticSearch 통합 검색, 필터링
3. **CompanyDetailPage** — 탭 기반 상세 (재무/공시/뉴스/평판)
4. **NewsFeedPage** — 뉴스 리스트 + NLP 감성분석 표시
5. **DealPipelinePage** — 딜 목록 + 섹터별 분류 + 트렌드 차트
6. **PortfolioPage** — 포트폴리오 현황 + 생존분석
7. **WatchlistPage** — 관심종목 + 알림 설정
8. **ReputationPage** — 기업 평판 스코어 대시보드
9. **hooks + types** 작성

**병렬 가능**: 1+2를 병렬, 3+4를 병렬, 5+6+7을 병렬, 8은 독립

### Phase 4: 크로스 모듈 연동 (3-4일)
> 3개 모듈 간 데이터 연결

1. **KIIS 기업정보 → IM 문서 생성** 연결 (기업 상세에서 "IM 생성" 버튼)
2. **FDD Deal → IM 문서** 연결 (딜 워크스페이스에서 IM 생성)
3. **KIIS 뉴스/평판 → FDD Issues** 연결 (이슈 참고자료로 링크)
4. **통합 대시보드** (홈 페이지에 3개 모듈 요약 표시)

---

## 재사용 컴포넌트 (Auto FDD에서)

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| Button, Badge, Card | `components/ui/` | 전 모듈 공통 |
| KpiCard | `components/ui/KpiCard.tsx` | 대시보드 KPI |
| DataTable | `components/ui/DataTable.tsx` | 목록 페이지 |
| Modal | `components/ui/Modal.tsx` | 생성/편집 다이얼로그 |
| Skeleton | `components/ui/Skeleton.tsx` | 로딩 상태 |
| EmptyState | `components/ui/EmptyState.tsx` | 빈 목록 |
| WaterfallChart | `components/charts/WaterfallChart.tsx` | KIIS 재무 차트 |
| FinancialBarChart | `components/charts/FinancialBarChart.tsx` | KIIS/IM 차트 |
| WorkflowStepper | `components/workflow/WorkflowStepper.tsx` | IM 파이프라인 진행률 |
| AuthProvider | `components/auth/AuthProvider.tsx` | 통합 인증 |
| AppShell + Sidebar | `components/layout/` | 전체 레이아웃 |

---

## 기술 스택 (확정)

- **Framework**: React 19 + TypeScript 5.7 (strict)
- **Build**: Vite 6
- **Routing**: React Router v7 (lazy loading)
- **State**: TanStack Query v5
- **Styling**: Tailwind CSS 3.4 (AMIC 브랜드)
- **Charts**: Recharts 3.7
- **Icons**: Lucide React
- **HTTP**: Axios (팩토리 패턴)
- **Auth**: JWT + refresh token
- **Deploy**: Docker + Nginx 리버스 프록시

---

## 검증 방법

1. **Phase 1 완료 후**: 기존 FDD 기능이 `/fdd/*` 경로에서 100% 동작하는지 확인
2. **Phase 2 완료 후**: IM 문서 생성 → 진행률 추적 → 다운로드 E2E 테스트
3. **Phase 3 완료 후**: KIIS 기업 검색 → 상세 조회 → 뉴스/평판 확인
4. **Phase 4 완료 후**: 모듈 간 이동 + 크로스 링크 동작 확인
5. **전체**: `npm run lint` (zero warnings) + `npm run build` (타입 에러 없음)

---

## 전제 조건 / 의존성

- ~~IM Module API 레이어 구축 필요 (현재 0%)~~ → ✅ API 100% 완료 (Phase 6, 207 테스트 통과)
- 3개 백엔드의 JWT secret 통일 필요
- Docker Compose에 3개 백엔드 서비스 추가
- ~~IM Module: narrative_generator, chart_engine 등 미완성 모듈~~ → ✅ 전체 모듈 구현 완료 (7개 코어 + API, 902 테스트 통과)
