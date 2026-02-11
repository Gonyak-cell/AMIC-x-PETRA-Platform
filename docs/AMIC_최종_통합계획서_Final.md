# AMIC x PETRA Platform — 최종 통합 계획서 (Final)

> 📌 본 문서는 3개 계획서의 모든 장점을 합친 최종 확정 계획서입니다.
> - 구조 설계: `unified-frontend-integration-plan.md`
> - API 매핑/페이지 명세: `AMIC_통합계획서.md`
> - 타입 정의/REITs/실용적 접근: `frontend-integration-plan.md`

---

## 1. 개요

AMIC Law 내부팀이 사용하는 3개 독립 프로젝트를 **AMIC x PETRA Platform**이라는 하나의 통합 프론트엔드로 합친다.

| 프로젝트 | 역할 | 포트 |
|----------|------|------|
| **Auto FDD** | 재무 실사 (Financial Due Diligence) | :8000 |
| **KIIS** | 투자 인텔리전스 (Investment Intelligence) | :8001 |
| **IM Module** | 투자설명서 생성 (Information Memorandum Generator) | :8002 |

Auto FDD의 프론트엔드(React 19 + TS + Vite, 프로덕션 수준)를 기반으로 확장하며, 백엔드는 각각 독립 서버로 운영한다.

---

## 2. 프론트엔드 현황 평가

### 2.1 Auto FDD (유일한 프론트엔드 보유)

| 항목 | 내용 |
|------|------|
| **프레임워크** | React 19 + Vite 6 + TypeScript 5.7 |
| **스타일링** | Tailwind CSS 3.4 (AMIC 커스텀 디자인 토큰) |
| **상태관리** | TanStack React Query 5 (서버 상태) |
| **라우팅** | React Router 7 (중첩 라우트, ProtectedRoute) |
| **차트** | Recharts 3 (FinancialBarChart, TrendLineChart, WaterfallChart) |
| **아이콘** | Lucide React |
| **인증** | JWT + Auto-refresh (axios interceptor, 중복 refresh 방지) |
| **알림** | Sonner (toast) |
| **코드 품질** | ESLint 9 + Prettier 3, 타입 안전한 커스텀 hooks |
| **규모** | ~50 TSX + ~30 TS 파일, 15개 페이지, 33개 컴포넌트, 11개 훅 |
| **접근성** | ARIA role, aria-label, 키보드 네비게이션 (DataTable) |
| **디자인 시스템** | AMIC 브랜딩 (다크그린 사이드바, IBM Plex Mono 숫자 폰트) |
| **배포** | Docker + Nginx 멀티스테이지 빌드 |

**아키텍처 강점:**

- `components/ui/` : 재사용 UI 라이브러리 12개+ (Button, Card, Input, Select, Modal, DataTable, Badge, Skeleton, KpiCard, EmptyState, Breadcrumbs, LiveRegion)
- `components/charts/` : 금융 전용 차트 시스템 (Waterfall, Bar, TrendLine + 공용 색상 토큰)
- `components/layout/` : AppShell, Sidebar, PageHeader (반응형 + ARIA 접근성)
- `hooks/` : 도메인별 custom hooks (useDeals, useQoE, useNWC, useDebt, useMapping 등)
- `types/` : 엄격한 TypeScript 타입 정의 (deal, qoe, nwc, debt, vdr 등)
- `api/client.ts` : JWT auto-refresh, 중복 refresh 방지, 401 자동 처리

### 2.2 IM Module (프론트엔드 없음)

| 항목 | 내용 |
|------|------|
| **스택** | Python 3.11 + FastAPI + Celery + Redis |
| **목적** | M&A Information Memorandum(IM) 자동 생성 |
| **출력** | python-pptx (PPTX), WeasyPrint (PDF) |
| **데이터** | DART API, Playwright 웹 크롤링, LLM(LangChain) 내러티브 |
| **프론트엔드** | **없음** — CLI/API 전용 |
| **API 상태** | 라우트 미구현 (빈 `__init__.py`만 존재) |

핵심 모듈: `data_ingestor/`, `financial_engine/`, `narrative_generator/`, `chart_engine/`, `design_renderer/`

### 2.3 KIIS (프론트엔드 없음)

| 항목 | 내용 |
|------|------|
| **스택** | Python 3.11 + FastAPI + SQLAlchemy 2.0(async) + httpx |
| **목적** | DART/KOFIA/리츠 투자정보 통합 인텔리전스 API |
| **프론트엔드** | **없음** — API 전용 |
| **API 상태** | 구현 완료 (Company, DART, KOFIA, REITs, News) — ~80% |

### 2.4 평가 결론

| 기준 | Auto FDD | IM Module | KIIS |
|------|----------|-----------|------|
| 프론트엔드 존재 여부 | ✅ | ❌ | ❌ |
| UI 컴포넌트 라이브러리 | 12+ | N/A | N/A |
| 차트 시스템 | 3종 | N/A | N/A |
| 인증/라우팅 | JWT + Router | N/A | N/A |
| 디자인 시스템 | AMIC 브랜딩 | N/A | N/A |
| 접근성 | ARIA 지원 | N/A | N/A |
| 백엔드 API 완성도 | 완료 (17 라우터) | 미구현 (23 티켓) | 완료 (~80%) |
| **점수** | **85/100** | **0/100** | **0/100** |

**Auto FDD가 유일한 프론트엔드이며, UI 라이브러리/차트/인증/디자인 시스템이 모두 갖추어져 있으므로 이를 통합 기반으로 사용한다.**

---

## 3. KIIS 백엔드 API 현황

KIIS는 5개 도메인의 API가 이미 구현되어 프론트엔드 연동만 하면 된다.

### 3.1 Company (기업)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /companies` | 기업 목록 (검색, 법인구분 필터, 페이지네이션) |
| `GET /companies/{corp_code}` | 기업 상세 (CEO, 주소, 업종, 홈페이지 등) |

주요 필드: `corp_code`, `corp_name`, `stock_code`, `ceo_nm`, `corp_cls`(Y/K/N/E), `adres`, `hm_url`, `induty_code`, `est_dt`

### 3.2 DART (공시/재무/제재)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /dart/disclosures` | 공시 검색 (기간, 유형, 최종보고서 필터) |
| `GET /dart/financials` | 재무제표 (BS/IS/CF, 연결/개별, 당기/전기/전전기) |
| `GET /dart/sanctions` | 제재 내역 (유형, 일자, 기관) |

### 3.3 KOFIA (펀드)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /kofia/funds` | 펀드 목록 (운용사, 유형 필터, 만기 경고) |
| `GET /kofia/funds/{fund_code}` | 펀드 상세 + 운용인력 목록 |
| `GET /kofia/managers` | 운용 전문인력 목록 |

주요 필드: `fund_code`, `fund_name`, `fund_type`(blind/project), `company_name`, `total_amount`, `vintage_year`, `is_maturity_alert`, `management_fee_rate`, `performance_fee_rate`

### 3.4 REITs (리츠)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /reits` | 리츠 목록 (유형, 상태 필터, 자산비율 경고) |
| `GET /reits/{reits_code}` | 리츠 상세 + 보유 자산 목록 |
| `GET /reits/{reits_code}/assets` | 리츠 자산 내역 |

주요 필드: `reits_code`, `reits_name`, `reits_type`(self_managed/entrusted), `total_assets`, `real_estate_ratio`, `has_asset_ratio_warning`, `dividend_rate`, `status`(authorized/operating/dissolved)

### 3.5 News (뉴스)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /news` | 뉴스 목록 (감성점수 포함, 페이지네이션) |

주요 필드: `title`, `source`, `published_at`, `url`, `sentiment_score`(-1.0 ~ 1.0)

---

## 4. IM Module 백엔드 현황

API 라우트 **아직 미구현** (빈 `__init__.py`만 존재). 핵심 엔진 모듈은 구현됨.

### 필요한 API 엔드포인트 (7개)

| 엔드포인트 | 설명 |
|-----------|------|
| `POST /im/projects` | IM 프로젝트 생성 |
| `GET /im/projects` | IM 프로젝트 목록 |
| `POST /im/projects/{id}/collect` | 데이터 수집 (DART + 크롤링) |
| `POST /im/projects/{id}/analyze` | 재무 분석 실행 |
| `POST /im/projects/{id}/generate` | IM 문서 생성 |
| `GET /im/projects/{id}/status` | 진행 상태 (Celery task status) |
| `GET /im/projects/{id}/download` | 생성된 PPTX/PDF 다운로드 |

핵심 엔진 모듈 (구현 완료):
- `data_ingestor/` : DART + Playwright 크롤러
- `financial_engine/` : 재무 정규화 + 지표 산출
- `narrative_generator/` : LangChain RAG 내러티브
- `chart_engine/` : Plotly 차트
- `design_renderer/` : PPTX/PDF 조립

---

## 5. 아키텍처

### 5-1. 단일 React 앱 + 모듈별 분리 구조

- Auto FDD 프론트엔드를 확장 (새 프로젝트 생성 X)
- 기존 FDD 코드를 `modules/fdd/`로 이동하여 모듈별 분리
- `React.lazy()` + `Suspense`로 모듈별 코드 스플리팅
- React Router v7의 중첩 라우팅으로 모듈 분리: `/fdd/*`, `/kiis/*`, `/im/*`

### 5-2. 전체 아키텍처

```
┌───────────────────────────────────────────────────────────┐
│              AMIC x PETRA Platform (React SPA)                     │
│            localhost:5173 (dev) / nginx (prod)             │
├───────────────────────────────────────────────────────────┤
│                    ModuleSwitcher                          │
│     ┌──────────┐   ┌──────────┐   ┌──────────┐           │
│     │  FDD     │   │  KIIS    │   │  IM      │           │
│     │ /fdd/*   │   │ /kiis/*  │   │ /im/*    │           │
│     └────┬─────┘   └────┬─────┘   └────┬─────┘           │
│          │              │              │                   │
│     /api/fdd/*     /api/kiis/*    /api/im/*               │
│     Vite Proxy     Vite Proxy     Vite Proxy              │
└──────────┬──────────────┬──────────────┬──────────────────┘
           ↓              ↓              ↓
      Auto FDD        KIIS Backend    IM Module
      :8000            :8001            :8002
      (PostgreSQL)     (PostgreSQL      (PostgreSQL
                       +Redis+ES)       +Redis+Celery)
```

### 5-3. 통합 인증 전략

| 단계 | 전략 |
|------|------|
| **1차 (즉시)** | Auto FDD의 JWT 인증을 기본으로 사용. KIIS/IM 백엔드는 `AUTH_ENABLED=False`로 개발 |
| **2차 (추후)** | 3개 백엔드에 동일 `JWT_SECRET` 공유. 프론트엔드는 단일 토큰으로 3개 백엔드 접근 |

---

## 6. 코딩 컨벤션

### 6.1 Money Rules (금융 앱 핵심 규칙)

```
⚠️ 모든 금액 필드는 string 타입 사용 — NEVER float
```

백엔드 Pydantic 스키마의 금액 필드가 `string`이므로, TypeScript에서도 반드시 `string | null`로 정의한다. 프론트엔드에서 표시할 때만 `Intl.NumberFormat`으로 포맷팅.

### 6.2 타입 정의 원칙

- KIIS 백엔드 Pydantic 스키마를 1:1 매핑하여 TypeScript interface로 정의
- 모든 필드를 빠짐없이 정의 (부분 타입 금지)
- `null` 가능성이 있는 필드는 명시적으로 `| null` 표기

### 6.3 기존 코드 패턴 준수

- hooks: 기존 `useDeals.ts` 패턴(useQuery + axios) 그대로 따름
- 페이지: 기존 `DealListPage.tsx` 패턴 참고
- 컴포넌트: 기존 `components/ui/` 최대 재사용

---

## 7. 디렉토리 구조

```
amic-platform/src/
├── api/
│   ├── client.ts              ← 수정: createApiClient() 팩토리 함수
│   ├── fddClient.ts           ← 새로: /api/fdd 인스턴스
│   ├── imClient.ts            ← 새로: /api/im 인스턴스
│   └── kiisClient.ts          ← 새로: /api/kiis 인스턴스
│
├── components/
│   ├── auth/                  ← 재사용 (AuthProvider, ProtectedRoute)
│   ├── layout/
│   │   ├── AppShell.tsx       ← 수정: 타이틀 "AMIC x PETRA Platform"
│   │   ├── Sidebar.tsx        ← 수정: ModuleSwitcher + 동적 네비게이션
│   │   ├── ModuleSwitcher.tsx ← 새로: FDD/KIIS/IM 전환 드롭다운
│   │   └── PageHeader.tsx     ← 재사용
│   ├── ui/                    ← 전체 재사용 (14개 컴포넌트)
│   ├── charts/                ← 재사용 (Waterfall, Bar, TrendLine)
│   └── shared/                ← 새로: 모듈 간 공유 컴포넌트
│       ├── CompanySearch.tsx   ← 3모듈 공통 회사 검색 (KIIS + IM에서 재사용)
│       └── StatusTimeline.tsx  ← 작업 진행률 표시
│
├── modules/
│   ├── fdd/                   ← 기존 FDD 페이지들 이동
│   │   ├── pages/             ← 기존 15개 페이지 (수정 최소화)
│   │   ├── hooks/             ← 기존 11개 훅 (api 경로만 fddClient로 변경)
│   │   ├── types/             ← 기존 10개 타입 파일
│   │   └── FddRoutes.tsx      ← FDD 라우트 정의
│   │
│   ├── kiis/                  ← 새로: KIIS 프론트엔드
│   │   ├── pages/
│   │   │   ├── KiisDashboardPage.tsx
│   │   │   ├── CompanyListPage.tsx
│   │   │   ├── CompanyDetailPage.tsx
│   │   │   ├── FundListPage.tsx
│   │   │   ├── ReitsListPage.tsx
│   │   │   ├── NewsFeedPage.tsx
│   │   │   ├── DealSourcingPage.tsx
│   │   │   ├── SanctionsPage.tsx
│   │   │   └── WatchlistPage.tsx
│   │   ├── hooks/
│   │   │   ├── useKiisDashboard.ts
│   │   │   ├── useCompanies.ts
│   │   │   ├── useCompanyDetail.ts
│   │   │   ├── useFunds.ts
│   │   │   ├── useReits.ts
│   │   │   ├── useNews.ts
│   │   │   ├── useReputation.ts
│   │   │   ├── useKiisDeals.ts
│   │   │   ├── useSanctions.ts
│   │   │   └── useWatchlist.ts
│   │   ├── types/
│   │   │   └── intelligence.ts  ← 전체 인터페이스 코드 (Pydantic 1:1 매핑)
│   │   ├── components/
│   │   │   ├── ReputationBadge.tsx
│   │   │   ├── SentimentIndicator.tsx
│   │   │   └── CompanySearchBar.tsx
│   │   └── KiisRoutes.tsx
│   │
│   └── im/                    ← 새로: IM Module 프론트엔드
│       ├── pages/
│       │   ├── ImDashboardPage.tsx
│       │   ├── ImCreatePage.tsx
│       │   ├── ImStatusPage.tsx
│       │   ├── ImPreviewPage.tsx
│       │   └── ImTemplatePage.tsx
│       ├── hooks/
│       │   ├── useIMDocuments.ts
│       │   ├── useIMDocument.ts
│       │   └── useIMTemplates.ts
│       ├── types/
│       │   └── im.ts
│       ├── components/
│       │   ├── IMProgressTracker.tsx
│       │   └── IMPreview.tsx
│       └── ImRoutes.tsx
│
├── App.tsx                    ← 수정: 모듈별 lazy 라우팅
├── main.tsx                   ← 재사용
└── index.css                  ← 재사용
```

---

## 8. 기술 스택 (확정)

| 카테고리 | 기술 |
|----------|------|
| **Framework** | React 19 + TypeScript 5.7 (strict) |
| **Build** | Vite 6 |
| **Routing** | React Router v7 (lazy loading) |
| **State** | TanStack Query v5 |
| **Styling** | Tailwind CSS 3.4 (AMIC 브랜드) |
| **Charts** | Recharts 3 |
| **Icons** | Lucide React |
| **HTTP** | Axios (팩토리 패턴) |
| **Auth** | JWT + refresh token |
| **Toast** | Sonner |
| **Deploy** | Docker + Nginx 리버스 프록시 |

---

## 9. TypeScript 타입 정의 (KIIS — 전체 코드)

> KIIS 백엔드 Pydantic 스키마를 1:1 매핑. 모든 금액 필드는 `string` 타입.

**파일:** `modules/kiis/types/intelligence.ts`

```typescript
// ══════════════════════════════════════════════════
// 공통
// ══════════════════════════════════════════════════

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  size: number;
  items: T[];
}

// ══════════════════════════════════════════════════
// 기업 (Company)
// ══════════════════════════════════════════════════

export interface CompanyListItem {
  corp_code: string;
  corp_name: string;
  stock_code: string;
  modify_date: string;
}

export interface CompanyInfo {
  corp_code: string;
  corp_name: string;
  corp_name_eng: string;
  stock_name: string;
  stock_code: string;
  ceo_nm: string;
  corp_cls: string;       // Y:유가, K:코스닥, N:코넥스, E:기타
  jurir_no: string;
  bizr_no: string;
  adres: string;
  hm_url: string;
  ir_url: string;
  phn_no: string;
  induty_code: string;
  est_dt: string;
  acc_mt: string;
}

// ══════════════════════════════════════════════════
// 공시 (Disclosure)
// ══════════════════════════════════════════════════

export interface DisclosureItem {
  corp_code: string;
  corp_name: string;
  corp_cls: string;
  report_nm: string;
  rcept_no: string;
  flr_nm: string;
  rcept_dt: string;
  rm: string;
}

// ══════════════════════════════════════════════════
// 재무제표 (Financial Statement)
// ══════════════════════════════════════════════════

export interface FinancialStatementItem {
  rcept_no: string;
  bsns_year: string;
  sj_div: string;         // BS, IS, CF 등
  sj_nm: string;
  account_id: string;
  account_nm: string;
  thstrm_nm: string;
  thstrm_amount: string;  // ⚠️ 금액은 string (Money Rules)
  frmtrm_nm: string;
  frmtrm_amount: string;
  bfefrmtrm_nm: string;
  bfefrmtrm_amount: string;
}

// ══════════════════════════════════════════════════
// 제재 (Sanction)
// ══════════════════════════════════════════════════

export interface SanctionItem {
  corp_code: string;
  corp_name: string;
  sanctions_type: string;
  sanctions_detail: string;
  sanctions_date: string;
  sanctions_agency: string;
}

// ══════════════════════════════════════════════════
// 펀드 (Fund)
// ══════════════════════════════════════════════════

export interface FundListItem {
  fund_code: string;
  fund_name: string;
  fund_type: string;       // blind / project
  company_name: string;
  total_amount: string | null;  // ⚠️ 금액 string
  vintage_year: number | null;
  is_maturity_alert: boolean;
}

export interface FundItem extends FundListItem {
  fund_category: string;
  company_code: string;
  management_fee_rate: string | null;
  performance_fee_rate: string | null;
  established_date: string | null;
  maturity_date: string | null;
  is_active: boolean;
  description: string;
  source_url: string;
}

export interface FundManagerItem {
  manager_name: string;
  position: string;
  role: string;
  career_years: number | null;
  education: string;
  certifications: string;
  appointed_date: string | null;
  resigned_date: string | null;
  is_active: boolean;
}

export interface FundDetailResponse {
  fund: FundItem;
  managers: FundManagerItem[];
}

// ══════════════════════════════════════════════════
// 리츠 (REITs)
// ══════════════════════════════════════════════════

export interface REITsListItem {
  reits_code: string;
  reits_name: string;
  reits_type: string;      // self_managed / entrusted
  management_company: string;
  total_assets: string | null;  // ⚠️ 금액 string
  real_estate_ratio: string | null;
  has_asset_ratio_warning: boolean;
  status: string;          // authorized / operating / dissolved
  is_listed: boolean;
}

export interface REITsItem extends REITsListItem {
  establishment_date: string | null;
  listing_date: string | null;
  real_estate_amount: string | null;
  dividend_rate: string | null;
  dividend_payout_ratio: string | null;
  net_income: string | null;
  total_dividend: string | null;
  employee_count: number | null;
  source_url: string;
}

export interface REITsAssetItem {
  asset_name: string;
  asset_type: string;      // office/logistics/residential/retail/hotel/other
  asset_value: string | null;
  asset_ratio: string | null;
  location: string;
  acquisition_date: string | null;
}

export interface REITsDetailResponse {
  reits: REITsItem;
  assets: REITsAssetItem[];
}

// ══════════════════════════════════════════════════
// 뉴스 (News)
// ══════════════════════════════════════════════════

export interface NewsListItem {
  id: number;
  title: string;
  source: string;
  author: string | null;
  published_at: string | null;
  url: string;
  sentiment_score: number | null;  // -1.0 ~ +1.0
}

// ══════════════════════════════════════════════════
// 딜 소싱 (Deal Sourcing)
// ══════════════════════════════════════════════════

export interface DealSourcingItem {
  deal_id: string;
  company_name: string;
  sector: string;
  stage: string;
  deal_size: string | null;  // ⚠️ 금액 string
  status: string;
}

export interface SectorData {
  sector: string;
  count: number;
  total_amount: string | null;
}

export interface StageData {
  stage: string;
  count: number;
}

export interface DealTrendData {
  period: string;
  count: number;
  total_amount: string | null;
}

// ══════════════════════════════════════════════════
// 평판 (Reputation)
// ══════════════════════════════════════════════════

export interface ReputationScore {
  corp_code: string;
  corp_name: string;
  overall_score: number;      // 0 ~ 100
  trend: 'rising' | 'stable' | 'declining';
  news_sentiment_avg: number;
  disclosure_regularity: number;
  sanctions_count: number;
  last_updated: string;
}

// ══════════════════════════════════════════════════
// 워치리스트 (Watchlist)
// ══════════════════════════════════════════════════

export interface WatchlistItem {
  id: number;
  corp_code: string;
  corp_name: string;
  added_at: string;
  alert_enabled: boolean;
  notes: string | null;
}

export interface AlertItem {
  id: number;
  corp_code: string;
  corp_name: string;
  alert_type: string;
  message: string;
  created_at: string;
  is_read: boolean;
}
```

---

## 10. TypeScript 타입 정의 (IM Module)

**파일:** `modules/im/types/im.ts`

```typescript
export interface ImProject {
  id: string;
  company_name: string;
  corp_code: string;
  status: 'created' | 'collecting' | 'analyzing' | 'generating' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  output_format: 'pptx' | 'pdf' | 'both';
  template_id: string | null;
}

export interface ImProjectDetail extends ImProject {
  sections: ImSection[];
  pipeline_status: PipelineStatus;
  download_urls: DownloadUrls | null;
}

export interface ImSection {
  section_id: string;
  title: string;        // 14개 섹션 중 하나
  status: 'pending' | 'processing' | 'completed' | 'failed';
  narrative: string | null;
  charts: string[];     // chart URLs
}

export interface PipelineStatus {
  current_step: number;  // 1~5
  total_steps: 5;
  steps: PipelineStep[];
}

export interface PipelineStep {
  step: number;
  name: string;          // 수집/분석/내러티브/차트/조립
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_pct: number;  // 0~100
  started_at: string | null;
  completed_at: string | null;
}

export interface DownloadUrls {
  pptx: string | null;
  pdf: string | null;
}

export interface ImTemplate {
  id: string;
  name: string;
  description: string;
  sections: string[];
  created_at: string;
  is_default: boolean;
}
```

---

## 11. 구현 계획

### Phase 1: 플랫폼 기반 구축 (3~4일) ✅ COMPLETE

> 기존 FDD 기능을 깨뜨리지 않으면서 확장 가능한 구조로 리팩토링

#### 1-1. 프로젝트 복사 및 리브랜딩

- `Auto FDD_backup/frontend/` → 새 위치에 `amic-platform/` 복사
- `package.json` name을 `amic-platform`으로 변경
- 사이드바 로고/타이틀을 "AMIC x PETRA Platform"으로 변경

#### 1-2. 모듈 구조 분리

- 기존 `src/pages/`, `src/hooks/`, `src/types/`를 `src/modules/fdd/`로 이동
- import 경로 일괄 수정
- `FddRoutes.tsx` 생성하여 FDD 라우트 독립 정의

#### 1-3. API Client 팩토리화

**수정 파일:** `src/api/client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

// 기존 인터셉터 로직을 공통 함수로 추출
function applyAuthInterceptors(instance: AxiosInstance) {
  // 요청: JWT 토큰 첨부
  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // 응답: 401 시 자동 리프레시 (중복 방지 포함)
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      // 기존 refresh 로직 유지
      // ...
    }
  );

  return instance;
}

export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({ baseURL });
  return applyAuthInterceptors(instance);
}

// 기존 호환용 alias
export const api = createApiClient('/api/fdd');
```

**새 파일 3개:**

```typescript
// src/api/fddClient.ts
import { createApiClient } from './client';
export const fddApi = createApiClient('/api/fdd');

// src/api/kiisClient.ts
import { createApiClient } from './client';
export const kiisApi = createApiClient('/api/kiis');

// src/api/imClient.ts
import { createApiClient } from './client';
export const imApi = createApiClient('/api/im');
```

#### 1-4. Vite 프록시 설정 (멀티 백엔드)

**수정 파일:** `vite.config.ts`

```typescript
export default defineConfig({
  // ...
  server: {
    proxy: {
      '/api/fdd': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/fdd/, '/api/v1'),
      },
      '/api/kiis': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/kiis/, '/api/v1'),
      },
      '/api/im': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/im/, '/api/v1'),
      },
    },
  },
});
```

#### 1-5. 사이드바 + ModuleSwitcher

- 상단에 **ModuleSwitcher** 드롭다운 추가 (FDD / KIIS / IM 전환)
- 네비게이션 아이템을 현재 모듈에 따라 동적 렌더링
- 네비게이션 config를 각 모듈의 Routes 파일에서 export

#### 1-6. App.tsx 라우팅 (Lazy Loading)

**수정 파일:** `src/App.tsx`

```typescript
import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';
import { Skeleton } from './components/ui/Skeleton';

const FddRoutes = React.lazy(() => import('./modules/fdd/FddRoutes'));
const KiisRoutes = React.lazy(() => import('./modules/kiis/KiisRoutes'));
const ImRoutes = React.lazy(() => import('./modules/im/ImRoutes'));

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
        <Route index element={<Navigate to="/fdd/deals" />} />
        <Route path="fdd/*" element={
          <Suspense fallback={<Skeleton className="h-full" />}>
            <FddRoutes />
          </Suspense>
        } />
        <Route path="kiis/*" element={
          <Suspense fallback={<Skeleton className="h-full" />}>
            <KiisRoutes />
          </Suspense>
        } />
        <Route path="im/*" element={
          <Suspense fallback={<Skeleton className="h-full" />}>
            <ImRoutes />
          </Suspense>
        } />
      </Route>
    </Routes>
  );
}
```

#### Phase 1 검증 체크리스트

- [x] 기존 FDD 기능이 `/fdd/*` 경로에서 100% 동작
- [x] 3개 백엔드 프록시 정상 동작 (브라우저 Network 탭)
- [x] ModuleSwitcher로 모듈 전환 시 사이드바 메뉴 변경
- [x] `npm run build` 성공 (타입 에러 없음)
- [x] `npm run lint` — 0 warnings

**병렬 가능:** 1-1 + 1-2를 병렬, 1-3 + 1-4를 병렬, 1-5는 독립

---

### Phase 2: KIIS 프론트엔드 구현 (7~10일)

> KIIS 백엔드는 ~80% 완성이므로 바로 연동 가능. IM Module보다 먼저 진행.

#### 2-1. 새로 만들 페이지 (9개)

| 페이지 | 경로 | KIIS API 엔드포인트 | 재사용 컴포넌트 | UI 상세 |
|--------|------|---------------------|-----------------|---------|
| **Dashboard** | `/kiis` | GET `/dashboard/summary` | KpiCard, charts | 기업 검색 바, KPI 행(기업수/펀드수/리츠수/뉴스건수), 최근 뉴스(감성점수 컬러코딩), 만기임박 펀드 경고, 자산비율 미달 리츠 경고 |
| **Company List** | `/kiis/companies` | GET `/companies`, `/search` | DataTable, Input, Select | 검색 Input + 법인구분 Select(유가/코스닥/코넥스/기타), 행 클릭→상세 |
| **Company Detail** | `/kiis/companies/:corpCode` | GET `/companies/{corp_code}`, `/dart/disclosures`, `/dart/financials`, `/dart/sanctions`, `/analysis/reputation/{corp_code}` | Card, Badge, 탭 UI, FinancialBarChart | 탭 기반(기본정보/공시/재무/제재/평판), 재무 탭에서 FinancialBarChart 활용, "IM 생성" CTA 버튼 |
| **Fund List** | `/kiis/funds` | GET `/kofia/funds` | DataTable, Badge, Modal | 운용사 검색 + 유형 Select(블라인드/프로젝트), 만기경고 Badge, 행 클릭→Modal(펀드상세 + 운용인력 DataTable) |
| **REITs List** | `/kiis/reits` | GET `/reits` | DataTable, Badge, Modal | 유형 Select(자기관리/위탁관리) + 상태 Select(인가/영업/해산), 자산비율 경고 Badge, 행 클릭→Modal(리츠상세 + 보유자산 DataTable) |
| **News Feed** | `/kiis/news` | GET `/news` | DataTable, Badge | 뉴스 리스트 + 감성점수 SentimentIndicator(-1.0~+1.0 컬러코딩: 양수=초록, 음수=빨강) |
| **Deal Sourcing** | `/kiis/deals` | GET `/deals/by-sector`, `/deals/by-stage`, `/deals/trends` | Charts (Bar, TrendLine) | 섹터별 분류 바차트, 스테이지별 분류, 트렌드 라인차트 |
| **Sanctions** | `/kiis/sanctions` | GET `/dart/sanctions` | DataTable, Badge | 제재 유형/기관/일자 필터, 제재 상세 Badge |
| **Watchlist** | `/kiis/watchlist` | GET/POST/DELETE `/watchlist`, GET `/alerts` | DataTable, Modal | 관심종목 추가/삭제, 알림 설정 토글, 알림 목록 |

#### 2-2. 새로 만들 훅 (10개)

| 훅 | API 클라이언트 | 주요 엔드포인트 |
|----|---------------|-----------------|
| `useKiisDashboard` | `kiisApi` | GET `/dashboard/summary` |
| `useCompanies` | `kiisApi` | GET `/companies` (search, corp_cls, page, size) |
| `useCompanyDetail` | `kiisApi` | GET `/companies/{corp_code}` |
| `useDisclosures` | `kiisApi` | GET `/dart/disclosures` (기간, 유형 필터) |
| `useFinancials` | `kiisApi` | GET `/dart/financials` (BS/IS/CF, 연결/개별) |
| `useFunds` | `kiisApi` | GET `/kofia/funds` (company_name, fund_type, page, size) |
| `useReits` | `kiisApi` | GET `/reits` (reits_type, status, page, size) |
| `useNews` | `kiisApi` | GET `/news` (page, size) |
| `useSanctions` | `kiisApi` | GET `/dart/sanctions` (corp_code) |
| `useWatchlist` | `kiisApi` | GET/POST/DELETE `/watchlist` |

기존 `useDeals.ts` 패턴(useQuery + axios) 그대로 따름:

```typescript
// 예시: useCompanies.ts
import { useQuery } from '@tanstack/react-query';
import { kiisApi } from '../../api/kiisClient';
import { PaginatedResponse, CompanyListItem } from '../types/intelligence';

interface UseCompaniesParams {
  search?: string;
  corp_cls?: string;
  page?: number;
  size?: number;
}

export function useCompanies(params: UseCompaniesParams = {}) {
  return useQuery<PaginatedResponse<CompanyListItem>>({
    queryKey: ['kiis', 'companies', params],
    queryFn: async () => {
      const { data } = await kiisApi.get('/companies', { params });
      return data;
    },
  });
}
```

#### 2-3. KIIS 전용 컴포넌트 (3개)

| 컴포넌트 | 용도 | 기반 |
|----------|------|------|
| `ReputationBadge` | Rising / Stable / Declining 상태 표시 (초록/회색/빨강) | 기존 Badge 확장 |
| `SentimentIndicator` | 감성 점수 -1.0 ~ +1.0 시각화 (그라데이션 바 + 숫자) | 신규 |
| `CompanySearchBar` | ElasticSearch 기반 통합 검색 (디바운스 + 자동완성) | 기존 Input 확장 |

#### 2-4. KIIS 라우트 정의

**파일:** `modules/kiis/KiisRoutes.tsx`

```typescript
import { Routes, Route } from 'react-router-dom';

export default function KiisRoutes() {
  return (
    <Routes>
      <Route index element={<KiisDashboardPage />} />
      <Route path="companies" element={<CompanyListPage />} />
      <Route path="companies/:corpCode" element={<CompanyDetailPage />} />
      <Route path="funds" element={<FundListPage />} />
      <Route path="reits" element={<ReitsListPage />} />
      <Route path="news" element={<NewsFeedPage />} />
      <Route path="deals" element={<DealSourcingPage />} />
      <Route path="sanctions" element={<SanctionsPage />} />
      <Route path="watchlist" element={<WatchlistPage />} />
    </Routes>
  );
}
```

#### Phase 2 검증 체크리스트

- [ ] KIIS Dashboard KPI 데이터 정상 로드
- [ ] 기업 검색 → 상세 조회 → 공시/재무/제재/평판 탭 E2E 동작
- [ ] 재무 탭에서 FinancialBarChart 렌더링 정상
- [ ] 펀드 목록 → Modal 상세(운용인력 포함) 동작
- [ ] 리츠 목록 → Modal 상세(보유자산 포함) 동작
- [ ] 뉴스 피드 감성점수 SentimentIndicator 렌더링
- [ ] 딜 소싱 차트 렌더링 정상
- [ ] Watchlist CRUD 동작
- [ ] 사이드바/DataTable 키보드 네비게이션 접근성 확인

**병렬 가능:** Dashboard + CompanyList를 병렬, CompanyDetail + NewsFeed를 병렬, FundList + ReitsListPage를 병렬, DealSourcing + Sanctions + Watchlist를 병렬

---

### Phase 3: IM Module 프론트엔드 구현 (5~7일)

> IM Module API 레이어 구축 필요 (현재 0%). Mock API로 병렬 진행 가능.

#### 3-1. 백엔드 API 선행 작업 (7개 엔드포인트)

| 엔드포인트 | 설명 |
|-----------|------|
| `POST /im/projects` | IM 프로젝트 생성 |
| `GET /im/projects` | IM 프로젝트 목록 |
| `POST /im/projects/{id}/collect` | 데이터 수집 (DART + 크롤링) |
| `POST /im/projects/{id}/analyze` | 재무 분석 실행 |
| `POST /im/projects/{id}/generate` | IM 문서 생성 |
| `GET /im/projects/{id}/status` | 진행 상태 (Celery task status) |
| `GET /im/projects/{id}/download` | 생성된 PPTX/PDF 다운로드 |

#### 3-2. 새로 만들 페이지 (5개)

| 페이지 | 경로 | IM API 엔드포인트 | 재사용 컴포넌트 | UI 상세 |
|--------|------|-------------------|-----------------|---------|
| **Project List** | `/im` | GET `/im/projects` | DataTable, Badge, KpiCard | 프로젝트 목록, 상태 Badge, KPI(총 프로젝트/진행중/완료) |
| **New IM Wizard** | `/im/new` | POST `/im/projects` | DealSetupWizard 패턴 | 4단계 위저드: ①기업 선택(KIIS CompanySearch 재사용) → ②기간 설정 → ③템플릿 선택 → ④생성 확인 |
| **IM Status** | `/im/:docId` | GET `/im/projects/{id}/status` | Card, WorkflowStepper | 5단계 파이프라인 진행률(수집/분석/내러티브/차트/조립), Celery polling |
| **IM Preview** | `/im/:docId/preview` | GET `/im/projects/{id}/download` | 신규 미리보기 | PPTX/PDF 미리보기 + 다운로드 버튼 |
| **Template Manager** | `/im/templates` | GET/POST `/templates` | DataTable, Modal | 템플릿 목록, 섹션 구성, 기본 템플릿 설정 |

#### 3-3. 새로 만들 훅 (3개)

| 훅 | API 클라이언트 | 주요 엔드포인트 |
|----|---------------|-----------------|
| `useIMDocuments` | `imApi` | GET/POST `/im/projects` |
| `useIMDocument` | `imApi` | GET `/im/projects/{id}/status`, GET `/im/projects/{id}/download` |
| `useIMTemplates` | `imApi` | GET/POST `/templates` |

#### 3-4. IM 전용 컴포넌트 (2개)

| 컴포넌트 | 용도 |
|----------|------|
| `IMProgressTracker` | Celery 작업 5단계 진행률 표시 (polling/SSE). 각 단계별 % + 경과시간 |
| `IMPreview` | 생성된 PPTX/PDF 미리보기 (iframe 또는 이미지 렌더링) + 다운로드 |

#### 3-5. IM 생성 위저드 상세 (4단계)

```
Step 1: 기업 선택
  → KIIS CompanySearch 컴포넌트 재사용
  → 선택 시 corp_code 저장

Step 2: 데이터 수집 기간 설정
  → 최근 3년/5년/사용자 지정 기간
  → POST /im/projects 호출 → 프로젝트 생성

Step 3: 섹션별 내러티브 미리보기/편집
  → 14개 섹션 리스트 (편집 가능)
  → 미완성 섹션은 "준비 중" 표시

Step 4: 문서 생성 & 다운로드
  → POST /im/projects/{id}/generate
  → IMProgressTracker로 진행률 추적
  → 완료 시 PPTX/PDF 다운로드
```

#### Phase 3 검증 체크리스트

- [ ] IM 프로젝트 목록 조회/생성 동작 (mock API)
- [ ] 위저드 4단계 정상 이동 + KIIS CompanySearch 연동
- [ ] 진행률 추적 (polling) 동작
- [ ] 문서 다운로드 동작
- [ ] 미완성 모듈은 "준비 중" 표시

**병렬 가능:** ProjectList + TemplatePage를 병렬, CreatePage + StatusPage를 병렬 (Preview는 Status 이후)

---

### Phase 4: 크로스 모듈 연동 (3~4일)

> 통합 플랫폼의 핵심 가치 — 3개 모듈 간 데이터 연결

#### 4-1. 모듈 간 연결

| 연동 | 설명 | 구현 |
|------|------|------|
| **KIIS → IM** | 기업 상세에서 "IM 생성" 버튼 | CompanyDetailPage에 CTA 버튼, `/im/new?corpCode=xxx`로 이동 |
| **FDD → IM** | 딜 워크스페이스에서 IM 생성 | DealWorkspacePage에 "IM 생성" 메뉴 추가 |
| **KIIS → FDD** | 뉴스/평판 데이터를 FDD Issues에 참고자료로 링크 | Issue 생성 시 KIIS 링크 첨부 |

#### 4-2. 통합 대시보드

홈 페이지(`/`)에 3개 모듈 요약 표시:

```
┌──────────────────────────────────────────────────┐
│                AMIC x PETRA Platform Home                 │
├──────────┬──────────────┬────────────────────────┤
│  FDD     │    KIIS      │       IM               │
│ KPI:     │ KPI:         │ KPI:                   │
│ 활성딜 N │ 등록기업 N   │ 생성된 IM N            │
│ 진행중 N │ 활성펀드 N   │ 진행중 N               │
│          │ 운영리츠 N   │                        │
│ 최근 딜  │ 최근 뉴스    │ 최근 IM 프로젝트       │
│ 바로가기 │ 바로가기     │ 바로가기               │
└──────────┴──────────────┴────────────────────────┘
```

#### Phase 4 검증 체크리스트

- [ ] KIIS 기업 상세 → "IM 생성" → IM 위저드로 이동 + corp_code 자동 입력
- [ ] FDD 딜 → "IM 생성" 연결 동작
- [ ] 통합 대시보드 3개 모듈 KPI 표시
- [ ] 모듈 간 이동 시 인증 유지

---

## 12. 사이드바 네비게이션 구조

> ModuleSwitcher 드롭다운으로 현재 모듈 선택 → 해당 모듈의 메뉴만 표시

### FDD 모드 선택 시

```
[ModuleSwitcher: FDD ▾]
├── Deals                    (Briefcase)
└── (deal workspace: setup, VDR, QoE, NWC, Report ...)
```

### KIIS 모드 선택 시

```
[ModuleSwitcher: KIIS ▾]
├── Dashboard                (BarChart3)
├── Companies                (Building2)
├── Funds                    (Wallet)
├── REITs                    (Building)
├── News & Sentiment         (Newspaper)
├── Deal Sourcing            (TrendingUp)
├── Sanctions                (ShieldAlert)
└── Watchlist                (Star)
```

### IM 모드 선택 시

```
[ModuleSwitcher: IM ▾]
├── Projects                 (FileText)
├── New IM                   (PlusCircle)
└── Templates                (Layout)
```

### 공통 (항상 하단 표시)

```
└── Settings
    └── Profile / Logout
```

---

## 13. 재사용 컴포넌트 목록 (Auto FDD에서)

| 컴포넌트 | 경로 | 사용처 |
|----------|------|--------|
| Button | `components/ui/Button.tsx` | 전 모듈 공통 |
| Badge | `components/ui/Badge.tsx` | 상태/경고 표시 (만기경고, 자산비율경고, 감성점수) |
| Card | `components/ui/Card.tsx` | 카드 레이아웃 |
| Input | `components/ui/Input.tsx` | 검색 입력 |
| Select | `components/ui/Select.tsx` | 필터 드롭다운 (법인구분, 펀드유형, 리츠유형 등) |
| KpiCard | `components/ui/KpiCard.tsx` | 모든 Dashboard KPI |
| DataTable | `components/ui/DataTable.tsx` | 모든 목록 페이지 (키보드 네비게이션, Skeleton 로딩) |
| Modal | `components/ui/Modal.tsx` | 펀드상세, 리츠상세, 생성/편집 다이얼로그 |
| Skeleton | `components/ui/Skeleton.tsx` | 로딩 상태 |
| EmptyState | `components/ui/EmptyState.tsx` | 빈 목록 |
| Breadcrumbs | `components/ui/Breadcrumbs.tsx` | 페이지 경로 표시 |
| LiveRegion | `components/ui/LiveRegion.tsx` | 접근성 알림 |
| FinancialBarChart | `components/charts/FinancialBarChart.tsx` | KIIS 재무 차트 |
| TrendLineChart | `components/charts/TrendLineChart.tsx` | KIIS 딜 트렌드 |
| WaterfallChart | `components/charts/WaterfallChart.tsx` | FDD/KIIS 재무 분석 |
| WorkflowStepper | `components/workflow/WorkflowStepper.tsx` | IM 파이프라인 진행률 |
| AuthProvider | `components/auth/AuthProvider.tsx` | 통합 인증 |
| AppShell + Sidebar | `components/layout/` | 전체 레이아웃 |

---

## 14. 전체 일정 요약

| Phase | 작업 | 기간 | 의존성 | 상태 |
|-------|------|------|--------|------|
| **1** | 플랫폼 기반 구축 (리브랜딩 + 모듈 분리 + API 팩토리 + 프록시 + ModuleSwitcher + 코드 스플리팅) | **3~4일** | 없음 | ✅ **COMPLETE** |
| **2** | KIIS 프론트엔드 (9페이지 + 10훅 + 타입 + 3컴포넌트) | **7~10일** | Phase 1 ✅ | ⬜ 미착수 |
| **3** | IM Module 프론트엔드 (5페이지 + 3훅 + 타입 + 2컴포넌트) + 백엔드 API 7개 | **5~7일** | Phase 1 ✅ | ⬜ 미착수 |
| **4** | 크로스 모듈 연동 (통합 대시보드 + 모듈 간 링크 3개) | **3~4일** | Phase 2, 3 | ⬜ 미착수 |

**총 예상 기간: 18~25일** (Phase 2 & 3 병렬 시)

```
Week 1       : [====== Phase 1 ======]
Week 2~3     : [========== Phase 2 (KIIS) ==========]
Week 2~3     :          [======= Phase 3 (IM) =======]  ← 병렬
Week 4       :                                    [== Phase 4 ==]
```

---

## 15. 파일 생성/수정 총정리

### 수정 (기존 파일, 7개)

| 파일 | 변경 내용 |
|------|-----------|
| `package.json` | name → "amic-platform" |
| `vite.config.ts` | 3개 백엔드 프록시 추가 |
| `src/api/client.ts` | `createApiClient()` 팩토리 함수로 리팩토링 |
| `src/App.tsx` | 모듈별 lazy 라우팅, FDD 경로 `/fdd/*` 변경 |
| `src/components/layout/Sidebar.tsx` | ModuleSwitcher + 동적 네비게이션 |
| `src/components/layout/AppShell.tsx` | 타이틀 "AMIC x PETRA Platform" |
| `src/modules/fdd/hooks/*.ts` | import 경로 fddClient로 변경 |

### 신규 (새 파일, ~40개)

| 카테고리 | 파일 | 개수 |
|----------|------|------|
| **API 클라이언트** | `fddClient.ts`, `imClient.ts`, `kiisClient.ts` | 3 |
| **레이아웃** | `ModuleSwitcher.tsx` | 1 |
| **공유 컴포넌트** | `CompanySearch.tsx`, `StatusTimeline.tsx` | 2 |
| **라우트** | `FddRoutes.tsx`, `KiisRoutes.tsx`, `ImRoutes.tsx` | 3 |
| **KIIS 타입** | `intelligence.ts` (전체 인터페이스 코드) | 1 |
| **KIIS 훅** | 10개 | 10 |
| **KIIS 페이지** | 9개 | 9 |
| **KIIS 컴포넌트** | `ReputationBadge`, `SentimentIndicator`, `CompanySearchBar` | 3 |
| **IM 타입** | `im.ts` (전체 인터페이스 코드) | 1 |
| **IM 훅** | 3개 | 3 |
| **IM 페이지** | 5개 | 5 |
| **IM 컴포넌트** | `IMProgressTracker`, `IMPreview` | 2 |
| **합계** | | **~43개** |

### 수정 불필요 — 재사용 컴포넌트 (18개)

| 컴포넌트 | 경로 |
|----------|------|
| Button, Badge, Card, Input, Select | `components/ui/` |
| KpiCard, DataTable, Modal | `components/ui/` |
| Skeleton, EmptyState, Breadcrumbs, LiveRegion | `components/ui/` |
| FinancialBarChart, TrendLineChart, WaterfallChart | `components/charts/` |
| WorkflowStepper | `components/workflow/` |
| AuthProvider, ProtectedRoute | `components/auth/` |
| AppShell, PageHeader | `components/layout/` |

---

## 16. 프로덕션 배포 (nginx + Docker Compose)

### nginx.conf

```nginx
server {
    listen 80;

    # Auto FDD Backend
    location /api/fdd/ {
        proxy_pass http://fdd-backend:8000/api/v1/;
    }

    # KIIS Backend
    location /api/kiis/ {
        proxy_pass http://kiis-backend:8001/api/v1/;
    }

    # IM Module Backend
    location /api/im/ {
        proxy_pass http://im-backend:8002/api/v1/;
    }

    # SPA fallback
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

### docker-compose.yml (추가 서비스)

```yaml
services:
  # 기존
  fdd-backend:
    build: ./Auto_FDD_backup/backend
    ports: ["8000:8000"]

  # 추가
  kiis-backend:
    build: ./KIIS_backup
    ports: ["8001:8001"]
    depends_on: [postgres, redis]

  im-backend:
    build: ./IM_Module_backup/backend
    ports: ["8002:8002"]
    depends_on: [postgres, redis, celery-worker]

  # 프론트엔드
  frontend:
    build: ./amic-platform
    ports: ["80:80"]
    depends_on: [fdd-backend, kiis-backend, im-backend]
```

---

## 17. 전제 조건 / 의존성

| 항목 | 상태 | 비고 |
|------|------|------|
| Auto FDD 프론트엔드 | ✅ 완성 | 기반 코드 |
| Auto FDD 백엔드 | ✅ 완성 | 17개 라우터 |
| KIIS 백엔드 | ⚠️ ~80% | 바로 연동 가능 |
| IM Module 백엔드 API | ❌ 0% | 7개 엔드포인트 구축 필요. Mock API로 병렬 진행 |
| 3개 백엔드 JWT_SECRET 통일 | ❌ 미완 | Phase 1에서 설정 |
| Docker Compose 3개 서비스 | ❌ 미완 | Phase 1에서 구성 |
| IM 미완성 모듈 (narrative_generator 등) | ❌ 미완 | 프론트엔드에서 "준비 중" 표시 |

---

## 18. 검증 방법

### 개발 서버 기동

```bash
# Terminal 1: Auto FDD Backend
cd "Auto FDD_backup/backend" && uv run uvicorn app.main:app --port 8000

# Terminal 2: KIIS Backend
cd KIIS_backup && uv run uvicorn app.main:app --port 8001

# Terminal 3: IM Module Backend (구축 후)
cd IM_Module_backup/backend && uv run uvicorn app.main:app --port 8002

# Terminal 4: Frontend
cd amic-platform && npm run dev
```

### 전체 검증 체크리스트

| 단계 | 검증 항목 |
|------|-----------|
| Phase 1 완료 ✅ | 기존 FDD 기능 `/fdd/*`에서 100% 동작 (회귀 테스트) |
| Phase 1 완료 ✅ | 3개 백엔드 프록시 정상 분기 (브라우저 Network 탭) |
| Phase 1 완료 ✅ | ModuleSwitcher 동작 + 사이드바 메뉴 동적 변경 |
| Phase 2 완료 | KIIS Dashboard KPI 로드 + 경고 리스트 표시 |
| Phase 2 완료 | 기업 검색 → 상세(공시/재무/제재/평판 탭) E2E |
| Phase 2 완료 | 재무 탭 FinancialBarChart 렌더링 |
| Phase 2 완료 | 펀드 목록 → Modal 상세(운용인력) 동작 |
| Phase 2 완료 | 리츠 목록 → Modal 상세(보유자산) 동작 |
| Phase 2 완료 | 뉴스 피드 감성점수 SentimentIndicator |
| Phase 2 완료 | Watchlist CRUD + 알림 |
| Phase 2 완료 | 사이드바/DataTable 키보드 네비게이션 접근성 |
| Phase 3 완료 | IM 위저드 4단계 + KIIS CompanySearch 연동 |
| Phase 3 완료 | IM 진행률 추적 (polling) 동작 |
| Phase 3 완료 | IM 문서 다운로드 동작 |
| Phase 4 완료 | KIIS → IM "IM 생성" 크로스 링크 |
| Phase 4 완료 | FDD → IM 크로스 링크 |
| Phase 4 완료 | 통합 대시보드 3모듈 KPI |
| 전체 | `npm run lint` — 0 warnings |
| 전체 | `npm run build` — 타입 에러 없음 |

---

## 19. 출처 및 각 문서 기여

| 요소 | 출처 |
|------|------|
| 모듈 분리 구조 (`modules/`) | `unified-frontend-integration-plan.md` |
| React.lazy() 코드 스플리팅 | `unified-frontend-integration-plan.md` |
| ModuleSwitcher 드롭다운 | `unified-frontend-integration-plan.md` |
| 크로스 모듈 연동 Phase 4 | `unified-frontend-integration-plan.md` |
| 일정 추정 | `unified-frontend-integration-plan.md` |
| KIIS 9페이지 API 매핑 테이블 | `AMIC_통합계획서.md` |
| KIIS 훅/타입/컴포넌트 명세 | `AMIC_통합계획서.md` |
| Vite 프록시/nginx 설정 코드 | `AMIC_통합계획서.md` |
| 사이드바 네비게이션 상세 | `AMIC_통합계획서.md` |
| TypeScript 인터페이스 전체 코드 | `frontend-integration-plan.md` |
| REITs 페이지 + API | `frontend-integration-plan.md` |
| Pydantic 1:1 매핑 원칙 | `frontend-integration-plan.md` |
| Money Rules (금액 string) | `frontend-integration-plan.md` |
| IM Module API 7개 엔드포인트 | `frontend-integration-plan.md` |
| 기존 컴포넌트 재사용 상세 목록 | `frontend-integration-plan.md` |
| 접근성 검증 항목 | `frontend-integration-plan.md` |
| KIIS 백엔드 5개 도메인 API 현황 | `frontend-integration-plan.md` |
| IM Module 핵심 엔진 모듈 현황 | `frontend-integration-plan.md` |
