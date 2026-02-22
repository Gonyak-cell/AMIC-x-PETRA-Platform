# AMIC x PETRA Platform — 전체 프로젝트 구조

---

## 1. 전체 그림 (Big Picture)

```
AMIC x PETRA Platform = 프론트엔드 1개 + 백엔드 3개 + 인프라

사용자 브라우저
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│              amic-platform/ (프론트엔드)                  │
│              React 19 + TypeScript + Vite                │
│              localhost:5173 (개발) / nginx (배포)         │
├─────────────────────────────────────────────────────────┤
│  /api/fdd/*       /api/kiis/*        /api/im/*          │
│      │                │                  │               │
│  Vite Proxy       Vite Proxy         Vite Proxy          │
└──────┬────────────────┬──────────────────┬──────────────┘
       ↓                ↓                  ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  Auto FDD    │ │    KIIS      │ │    IM Module     │
│  백엔드       │ │  백엔드       │ │    백엔드         │
│  FastAPI     │ │  FastAPI     │ │  FastAPI+Celery  │
│  :8000       │ │  :8001       │ │  :8002           │
│  PostgreSQL  │ │  PostgreSQL  │ │  PostgreSQL      │
│              │ │  +Redis+ES   │ │  +Redis+Celery   │
└──────────────┘ └──────────────┘ └──────────────────┘
```

---

## 2. 최상위 프로젝트 폴더 구조

```
AMIC-Platform/                          ← 최상위 루트
│
├── amic-platform/                      ← 🟦 통합 프론트엔드 (React)
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── Auto_FDD_backup/                    ← 🟩 FDD 백엔드 (Python)
│   └── backend/
│       ├── app/
│       ├── requirements.txt
│       └── Dockerfile
│
├── KIIS_backup/                        ← 🟨 KIIS 백엔드 (Python)
│   ├── app/
│   ├── requirements.txt
│   └── Dockerfile
│
├── IM_Module_backup/                   ← 🟥 IM Module 백엔드 (Python)
│   └── backend/
│       ├── app/
│       ├── requirements.txt
│       └── Dockerfile
│
├── docker-compose.yml                  ← 🐳 전체 서비스 오케스트레이션
├── config/
│   └── nginx/
│       └── default.conf                ← nginx 프록시 설정
│
└── README.md
```

---

## 3. 프론트엔드 상세 구조 (amic-platform/)

> 이 부분이 핵심! Auto FDD 프론트엔드를 확장한 통합 앱

```
amic-platform/
├── public/
│   └── favicon.ico
│
├── src/
│   │
│   ├── api/                            ← 🔌 API 클라이언트 (백엔드 통신)
│   │   ├── client.ts                   ← 🔧 수정: createApiClient() 팩토리 함수
│   │   ├── fddClient.ts               ← 🆕 /api/fdd 인스턴스
│   │   ├── kiisClient.ts              ← 🆕 /api/kiis 인스턴스
│   │   └── imClient.ts                ← 🆕 /api/im 인스턴스
│   │
│   ├── components/                     ← 🧩 공통 컴포넌트 (모든 모듈이 공유)
│   │   │
│   │   ├── auth/                       ← 인증 (재사용)
│   │   │   ├── AuthProvider.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   │
│   │   ├── layout/                     ← 레이아웃 (수정)
│   │   │   ├── AppShell.tsx            ← 🔧 수정: 타이틀 "AMIC x PETRA Platform"
│   │   │   ├── Sidebar.tsx             ← 🔧 수정: ModuleSwitcher + 동적 네비게이션
│   │   │   ├── ModuleSwitcher.tsx      ← 🆕 FDD/KIIS/IM 전환 드롭다운
│   │   │   └── PageHeader.tsx          ← 재사용
│   │   │
│   │   ├── ui/                         ← UI 라이브러리 (전체 재사용, 수정 없음)
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── DataTable.tsx           ← 키보드 네비게이션, Skeleton 로딩
│   │   │   ├── KpiCard.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   ├── Breadcrumbs.tsx
│   │   │   └── LiveRegion.tsx          ← 접근성 알림
│   │   │
│   │   ├── charts/                     ← 차트 (재사용, 수정 없음)
│   │   │   ├── FinancialBarChart.tsx
│   │   │   ├── TrendLineChart.tsx
│   │   │   ├── WaterfallChart.tsx
│   │   │   └── chartColors.ts         ← 공용 색상 토큰
│   │   │
│   │   ├── workflow/                   ← 워크플로우 (재사용)
│   │   │   └── WorkflowStepper.tsx
│   │   │
│   │   └── shared/                     ← 🆕 모듈 간 공유 컴포넌트
│   │       ├── CompanySearch.tsx        ← KIIS + IM에서 공통 사용
│   │       └── StatusTimeline.tsx       ← 작업 진행률 표시
│   │
│   ├── modules/                        ← 📦 모듈별 분리 (핵심 구조!)
│   │   │
│   │   ├── fdd/                        ← 🟩 FDD 모듈 (기존 코드 이동)
│   │   │   ├── pages/                  ← 기존 15개 페이지 (수정 최소화)
│   │   │   │   ├── DealListPage.tsx
│   │   │   │   ├── DealSetupWizardPage.tsx
│   │   │   │   ├── DealWorkspacePage.tsx
│   │   │   │   ├── QoEPage.tsx
│   │   │   │   ├── NWCPage.tsx
│   │   │   │   ├── DebtPage.tsx
│   │   │   │   ├── VDRPage.tsx
│   │   │   │   ├── ReportPage.tsx
│   │   │   │   └── ... (기존 페이지들)
│   │   │   │
│   │   │   ├── hooks/                  ← 기존 11개 훅 (import만 fddClient로 변경)
│   │   │   │   ├── useDeals.ts
│   │   │   │   ├── useQoE.ts
│   │   │   │   ├── useNWC.ts
│   │   │   │   ├── useDebt.ts
│   │   │   │   ├── useMapping.ts
│   │   │   │   └── ... (기존 훅들)
│   │   │   │
│   │   │   ├── types/                  ← 기존 10개 타입 파일
│   │   │   │   ├── deal.ts
│   │   │   │   ├── qoe.ts
│   │   │   │   ├── nwc.ts
│   │   │   │   ├── debt.ts
│   │   │   │   ├── vdr.ts
│   │   │   │   └── ...
│   │   │   │
│   │   │   └── FddRoutes.tsx           ← 🆕 FDD 라우트 정의
│   │   │
│   │   ├── kiis/                       ← 🟨 KIIS 모듈 (전부 신규)
│   │   │   ├── pages/                  ← 🆕 9개 페이지
│   │   │   │   ├── KiisDashboardPage.tsx    ← KPI + 경고 리스트 + 최근 뉴스
│   │   │   │   ├── CompanyListPage.tsx      ← 기업 검색/목록
│   │   │   │   ├── CompanyDetailPage.tsx    ← 탭(기본/공시/재무/제재/평판)
│   │   │   │   ├── FundListPage.tsx         ← 펀드 목록 + Modal 상세
│   │   │   │   ├── ReitsListPage.tsx        ← 리츠 목록 + Modal 상세
│   │   │   │   ├── NewsFeedPage.tsx         ← 뉴스 + 감성분석
│   │   │   │   ├── DealSourcingPage.tsx     ← 딜 소싱 + 트렌드 차트
│   │   │   │   ├── SanctionsPage.tsx        ← 제재 모니터링
│   │   │   │   └── WatchlistPage.tsx        ← 관심종목 + 알림
│   │   │   │
│   │   │   ├── hooks/                  ← 🆕 10개 훅
│   │   │   │   ├── useKiisDashboard.ts
│   │   │   │   ├── useCompanies.ts
│   │   │   │   ├── useCompanyDetail.ts
│   │   │   │   ├── useDisclosures.ts
│   │   │   │   ├── useFinancials.ts
│   │   │   │   ├── useFunds.ts
│   │   │   │   ├── useReits.ts
│   │   │   │   ├── useNews.ts
│   │   │   │   ├── useSanctions.ts
│   │   │   │   └── useWatchlist.ts
│   │   │   │
│   │   │   ├── types/                  ← 🆕 전체 인터페이스 코드
│   │   │   │   └── intelligence.ts     ← ~200줄 (Pydantic 1:1 매핑)
│   │   │   │
│   │   │   ├── components/             ← 🆕 KIIS 전용 컴포넌트 3개
│   │   │   │   ├── ReputationBadge.tsx      ← Rising/Stable/Declining
│   │   │   │   ├── SentimentIndicator.tsx   ← 감성 -1.0~+1.0
│   │   │   │   └── CompanySearchBar.tsx     ← ES 검색 + 자동완성
│   │   │   │
│   │   │   └── KiisRoutes.tsx          ← 🆕 KIIS 라우트 정의
│   │   │
│   │   └── im/                         ← 🟥 IM 모듈 (전부 신규)
│   │       ├── pages/                  ← 🆕 5개 페이지
│   │       │   ├── ImDashboardPage.tsx      ← IM 프로젝트 목록 + KPI
│   │       │   ├── ImCreatePage.tsx         ← 4단계 생성 위저드
│   │       │   ├── ImStatusPage.tsx         ← 5단계 파이프라인 진행률
│   │       │   ├── ImPreviewPage.tsx        ← PPTX/PDF 미리보기 + 다운로드
│   │       │   └── ImTemplatePage.tsx       ← 템플릿 관리
│   │       │
│   │       ├── hooks/                  ← 🆕 3개 훅
│   │       │   ├── useIMDocuments.ts
│   │       │   ├── useIMDocument.ts
│   │       │   └── useIMTemplates.ts
│   │       │
│   │       ├── types/                  ← 🆕 전체 인터페이스 코드
│   │       │   └── im.ts
│   │       │
│   │       ├── components/             ← 🆕 IM 전용 컴포넌트 2개
│   │       │   ├── IMProgressTracker.tsx    ← Celery 5단계 진행률
│   │       │   └── IMPreview.tsx            ← 문서 미리보기
│   │       │
│   │       └── ImRoutes.tsx            ← 🆕 IM 라우트 정의
│   │
│   ├── App.tsx                         ← 🔧 수정: 모듈별 lazy 라우팅
│   ├── main.tsx                        ← 재사용
│   └── index.css                       ← 재사용
│
├── package.json                        ← 🔧 수정: name → "amic-platform"
├── vite.config.ts                      ← 🔧 수정: 3개 백엔드 프록시
├── tailwind.config.ts                  ← 재사용
├── tsconfig.json                       ← 재사용
├── Dockerfile                          ← 재사용 (nginx 빌드)
└── nginx.conf                          ← 🔧 수정: 3개 백엔드 프록시
```

---

## 4. 백엔드 구조 (참고)

### 4-1. Auto FDD 백엔드 (:8000)

```
Auto_FDD_backup/backend/
├── app/
│   ├── main.py                     ← FastAPI 앱 진입점
│   ├── api/
│   │   └── v1/
│   │       ├── auth/               ← 인증 (JWT)
│   │       ├── deals/              ← 딜 CRUD
│   │       ├── qoe/                ← Quality of Earnings
│   │       ├── nwc/                ← Net Working Capital
│   │       ├── debt/               ← Net Debt
│   │       ├── vdr/                ← Virtual Data Room
│   │       ├── mapping/            ← 계정 매핑
│   │       └── reports/            ← 보고서 생성
│   ├── models/                     ← SQLAlchemy 모델
│   ├── schemas/                    ← Pydantic 스키마
│   ├── services/                   ← 비즈니스 로직
│   └── core/                       ← 설정, DB, 보안
├── requirements.txt
└── Dockerfile
```

**17개 라우터 모듈 완비. 프론트엔드 완전 연동 상태.**

### 4-2. KIIS 백엔드 (:8001)

```
KIIS_backup/
├── app/
│   ├── main.py                     ← FastAPI 앱 진입점
│   ├── api/
│   │   └── v1/
│   │       ├── companies/          ← 기업 목록/상세
│   │       ├── dart/               ← 공시/재무/제재
│   │       ├── kofia/              ← 펀드/운용인력
│   │       ├── reits/              ← 리츠/자산
│   │       └── news/               ← 뉴스/감성분석
│   ├── models/                     ← SQLAlchemy 2.0 (async)
│   ├── schemas/                    ← Pydantic 스키마
│   ├── services/                   ← 외부 API 연동 (DART, KOFIA, httpx)
│   └── core/                       ← 설정, DB
├── requirements.txt
└── Dockerfile
```

**5개 도메인 API 구현 완료 (~80%). 프론트엔드 연동만 하면 됨.**

### 4-3. IM Module 백엔드 (:8002)

```
IM_Module_backup/backend/
├── app/
│   ├── main.py                     ← FastAPI 앱 진입점
│   ├── api/
│   │   └── v1/
│   │       └── __init__.py         ← ⚠️ 비어있음! API 구축 필요
│   ├── data_ingestor/              ← ✅ DART + Playwright 크롤러
│   ├── financial_engine/           ← ✅ 재무 정규화 + 지표 산출
│   ├── narrative_generator/        ← ✅ LangChain RAG 내러티브
│   ├── chart_engine/               ← ✅ Plotly 차트
│   ├── design_renderer/            ← ✅ PPTX/PDF 조립
│   ├── models/
│   ├── schemas/
│   └── core/
├── celery_app.py                   ← Celery 워커 설정
├── requirements.txt
└── Dockerfile
```

**핵심 엔진은 구현됨. API 라우트 7개 구축 필요 (Phase 3 선행 작업).**

---

## 5. 인프라 구조

### 5-1. docker-compose.yml

```
docker-compose.yml
│
├── fdd-backend     (:8000)    ← Auto FDD FastAPI
├── kiis-backend    (:8001)    ← KIIS FastAPI
├── im-backend      (:8002)    ← IM Module FastAPI
├── celery-worker              ← IM Module Celery 워커
├── postgres        (:5432)    ← PostgreSQL (공유 또는 개별)
├── redis           (:6379)    ← Redis (KIIS 캐시 + Celery 브로커)
├── elasticsearch   (:9200)    ← KIIS 검색 엔진 (선택)
└── frontend        (:80)      ← nginx + React 빌드 결과물
```

### 5-2. 네트워크 흐름

```
[브라우저] → :80 (nginx)
                │
                ├── /api/fdd/*  → :8000 (Auto FDD)  → PostgreSQL
                ├── /api/kiis/* → :8001 (KIIS)       → PostgreSQL + Redis + ES
                ├── /api/im/*   → :8002 (IM Module)  → PostgreSQL + Redis + Celery
                └── /*          → React SPA (index.html)
```

### 5-3. 개발 환경 흐름

```
[브라우저] → :5173 (Vite dev server)
                │
                ├── /api/fdd/*  → Vite Proxy → :8000
                ├── /api/kiis/* → Vite Proxy → :8001
                ├── /api/im/*   → Vite Proxy → :8002
                └── /*          → Vite HMR (Hot Module Replacement)
```

---

## 6. 라우팅 전체 맵

### 프론트엔드 URL → 페이지 매핑

```
/login                          → LoginPage

/                               → 통합 대시보드 (Phase 4)
                                  또는 → /fdd/deals 리다이렉트

── FDD 모듈 ─────────────────────────────────────────
/fdd/deals                      → DealListPage
/fdd/deals/new                  → DealSetupWizardPage
/fdd/deals/:dealId/*            → DealWorkspacePage
  ├── /fdd/deals/:dealId/setup
  ├── /fdd/deals/:dealId/vdr
  ├── /fdd/deals/:dealId/qoe
  ├── /fdd/deals/:dealId/nwc
  ├── /fdd/deals/:dealId/debt
  └── /fdd/deals/:dealId/report

── KIIS 모듈 ────────────────────────────────────────
/kiis                           → KiisDashboardPage
/kiis/companies                 → CompanyListPage
/kiis/companies/:corpCode       → CompanyDetailPage (탭: 기본/공시/재무/제재/평판)
/kiis/funds                     → FundListPage (행 클릭 → Modal 상세)
/kiis/reits                     → ReitsListPage (행 클릭 → Modal 상세)
/kiis/news                      → NewsFeedPage
/kiis/deals                     → DealSourcingPage
/kiis/sanctions                 → SanctionsPage
/kiis/watchlist                 → WatchlistPage

── IM 모듈 ──────────────────────────────────────────
/im                             → ImDashboardPage (프로젝트 목록)
/im/new                         → ImCreatePage (4단계 위저드)
/im/:docId                      → ImStatusPage (파이프라인 진행률)
/im/:docId/preview              → ImPreviewPage (PPTX/PDF 미리보기)
/im/templates                   → ImTemplatePage
```

### API 프록시 → 백엔드 매핑

```
프론트엔드 요청                  → 실제 백엔드 URL
─────────────────────────────────────────────────
/api/fdd/companies               → :8000/api/v1/companies
/api/fdd/deals                   → :8000/api/v1/deals
/api/fdd/auth/login              → :8000/api/v1/auth/login

/api/kiis/companies              → :8001/api/v1/companies
/api/kiis/dart/financials        → :8001/api/v1/dart/financials
/api/kiis/kofia/funds            → :8001/api/v1/kofia/funds
/api/kiis/reits                  → :8001/api/v1/reits
/api/kiis/news                   → :8001/api/v1/news

/api/im/projects                 → :8002/api/v1/projects
/api/im/projects/:id/status      → :8002/api/v1/projects/:id/status
/api/im/projects/:id/download    → :8002/api/v1/projects/:id/download
```

---

## 7. 숫자로 보는 전체 규모

### 프론트엔드

| 항목 | 기존 (FDD만) | 통합 후 (FDD+KIIS+IM) |
|------|-------------|----------------------|
| **페이지** | 15개 | **29개** (+14) |
| **훅** | 11개 | **24개** (+13) |
| **타입 파일** | 10개 | **12개** (+2) |
| **전용 컴포넌트** | 0개 | **5개** (+5) |
| **공유 컴포넌트** | 33개 | **35개** (+2) |
| **API 클라이언트** | 1개 | **3개** (+2) |
| **라우트 파일** | 0개 | **3개** (+3) |
| **레이아웃** | 3개 | **4개** (+1 ModuleSwitcher) |
| **총 신규 파일** | - | **~43개** |

### 백엔드

| 항목 | FDD | KIIS | IM Module | 합계 |
|------|-----|------|-----------|------|
| **API 라우터** | 17개 | 5개 도메인 | 7개 (구축 필요) | **29개** |
| **상태** | ✅ 완료 | ⚠️ ~80% | ❌ API 0% | - |

### 인프라

| 서비스 | 개수 |
|--------|------|
| Docker 컨테이너 | 6~7개 (백엔드 3 + DB 1 + Redis 1 + Celery 1 + Frontend 1) |
| 포트 | 5개 (:80, :8000, :8001, :8002, :5432) |
| 프록시 경로 | 3개 (/api/fdd, /api/kiis, /api/im) |

---

## 8. 구현 현황 (Phase Status)

### Phase 1: 플랫폼 기반 구축 ✅ COMPLETE

| 항목 | 상태 | 구현 내용 |
|------|------|-----------|
| 모듈 구조 분리 | ✅ | `src/modules/fdd/`, `kiis/`, `im/` 3개 모듈 디렉토리 |
| API 팩토리 | ✅ | `createApiClient(baseURL)` + `fddClient`, `kiisClient`, `imClient` |
| Vite 프록시 | ✅ | `/api/fdd` → :8000, `/api/kiis` → :8001, `/api/im` → :8002 |
| ModuleSwitcher | ✅ | 드롭다운으로 FDD/KIIS/IM 모듈 전환 |
| 동적 사이드바 | ✅ | URL prefix 기반 자동 네비게이션 변경 |
| Lazy Loading | ✅ | React.lazy + Suspense로 모듈별 코드 스플리팅 |
| FDD 훅 | ✅ | 9개 훅 생성 (useDeals, useQoE, useNWC, useDebt, useVdr, useIssues, useMapping, useUploads, useReportVersions) |
| FDD 페이지 이동 | ✅ | 15개 페이지 → `modules/fdd/pages/` |
| FDD 타입 이동 | ✅ | 9개 타입 → `modules/fdd/types/` |
| FDD 라우트 | ✅ | `FddRoutes.tsx` 독립 라우트 정의 |
| KIIS/IM 스텁 라우트 | ✅ | `KiisRoutes.tsx`, `ImRoutes.tsx` 스텁 생성 |

### Phase 2: KIIS 프론트엔드 ⬜ 미착수

### Phase 3: IM Module 프론트엔드 ⬜ 미착수

### Phase 4: 크로스 모듈 연동 ⬜ 미착수
