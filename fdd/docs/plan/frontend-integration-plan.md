# 프론트엔드 통합 계획: Auto FDD + KIIS + IM Module

> 작성일: 2026년 02월 09일 20시 18분 10초

---

## 1. 배경

Auto FDD, IM Module, KIIS 세 프로젝트의 프론트엔드를 통합하려는 요구.
코드베이스 전수 조사 결과, **Auto FDD만 프론트엔드(React)가 존재**하며
IM Module과 KIIS는 Python FastAPI 백엔드 전용 프로젝트임이 확인됨.

따라서 **Auto FDD 프론트엔드를 기반으로 나머지 두 프로젝트의 기능을 모듈로 추가**하는 방식을 채택.
KIIS 인텔리전스 모듈을 먼저 통합한 후, IM Module을 후속 통합한다.

---

## 2. 3개 프로젝트 프론트엔드 비교 평가

### 2.1 Auto FDD (유일한 프론트엔드 보유)

| 항목 | 내용 |
| ---- | ---- |
| 프레임워크 | React 19 + Vite 6 + TypeScript 5.7 |
| 스타일링 | Tailwind CSS 3.4 (AMIC 커스텀 디자인 토큰) |
| 상태관리 | TanStack React Query 5 (서버 상태) |
| 라우팅 | React Router 7 (중첩 라우트, ProtectedRoute) |
| 차트 | Recharts 3 (FinancialBarChart, TrendLineChart, WaterfallChart) |
| 아이콘 | Lucide React |
| 인증 | JWT + Auto-refresh (axios interceptor, 중복 refresh 방지) |
| 알림 | Sonner (toast) |
| 코드 품질 | ESLint 9 + Prettier 3, 타입 안전한 커스텀 hooks |
| 규모 | ~50 TSX + ~30 TS 파일 |

**아키텍처 강점:**

- `components/ui/` : 재사용 UI 라이브러리 12개+ (Button, Card, Input, Select, Modal, DataTable, Badge, Skeleton, KpiCard, EmptyState, Breadcrumbs, LiveRegion)
- `components/charts/` : 금융 전용 차트 시스템 (Waterfall, Bar, TrendLine + 공용 색상 토큰)
- `components/layout/` : AppShell, Sidebar, PageHeader (반응형 + ARIA 접근성)
- `hooks/` : 도메인별 custom hooks (useDeals, useQoE, useNWC, useDebt, useMapping 등)
- `types/` : 엄격한 TypeScript 타입 정의 (deal, qoe, nwc, debt, vdr 등)
- `api/client.ts` : JWT auto-refresh, 중복 refresh 방지, 401 자동 처리
- 접근성: ARIA role, aria-label, 키보드 네비게이션 (DataTable)
- 디자인 시스템: AMIC 브랜딩 (다크그린 사이드바, IBM Plex Mono 숫자 폰트)

### 2.2 IM Module (프론트엔드 없음)

| 항목 | 내용 |
| ---- | ---- |
| 스택 | Python 3.11 + FastAPI + Celery + Redis |
| 목적 | M&A Information Memorandum(IM) 자동 생성 |
| 출력 | python-pptx (PPTX), WeasyPrint (PDF) |
| 데이터 | DART API, Playwright 웹 크롤링, LLM(LangChain) 내러티브 |
| 프론트엔드 | **없음** — CLI/API 전용 |
| API 상태 | 라우트 미구현 (빈 `__init__.py`만 존재) |

핵심 모듈:
- `data_ingestor/` : DART API, 문서 파싱, 웹 크롤링
- `financial_engine/` : 재무 데이터 정규화, 파생지표 산출
- `narrative_generator/` : RAG 기반 내러티브 생성
- `chart_engine/` : Plotly 차트, Graphviz 다이어그램
- `design_renderer/` : PPTX/PDF 문서 조립, 폰트/디자인 토큰 시스템

### 2.3 KIIS (프론트엔드 없음)

| 항목 | 내용 |
| ---- | ---- |
| 스택 | Python 3.11 + FastAPI + SQLAlchemy 2.0(async) + httpx |
| 목적 | DART/KOFIA/리츠 투자정보 통합 인텔리전스 API |
| 출력 | JSON API 응답 |
| 데이터 | DART API, KOFIA API, 리츠정보시스템, 뉴스 크롤링 |
| 프론트엔드 | **없음** — API 전용 |
| API 상태 | 구현 완료 (Company, DART, KOFIA, REITs, News) |

### 2.4 평가 결론

| 기준 | Auto FDD | IM Module | KIIS |
| ---- | -------- | --------- | ---- |
| 프론트엔드 존재 여부 | O | X | X |
| UI 컴포넌트 라이브러리 | 12+ | N/A | N/A |
| 차트 시스템 | 3종 | N/A | N/A |
| 인증/라우팅 | JWT + Router | N/A | N/A |
| 디자인 시스템 | AMIC 브랜딩 | N/A | N/A |
| 접근성 | ARIA 지원 | N/A | N/A |
| 백엔드 API 완성도 | 완료 | 미구현 | 완료 |

**Auto FDD가 유일한 프론트엔드이며, UI 라이브러리/차트/인증/디자인 시스템이 모두 갖추어져 있으므로 이를 통합 기반으로 사용한다.**

---

## 3. KIIS 백엔드 API 현황

KIIS는 5개 도메인의 API가 이미 구현되어 프론트엔드 연동만 하면 된다.

### 3.1 Company (기업)

| 엔드포인트 | 설명 |
| ---- | ---- |
| `GET /companies` | 기업 목록 (검색, 법인구분 필터, 페이지네이션) |
| `GET /companies/{corp_code}` | 기업 상세 (CEO, 주소, 업종, 홈페이지 등) |

주요 필드: `corp_code`, `corp_name`, `stock_code`, `ceo_nm`, `corp_cls`(Y/K/N/E), `adres`, `hm_url`, `induty_code`, `est_dt`

### 3.2 DART (공시/재무/제재)

| 엔드포인트 | 설명 |
| ---- | ---- |
| `GET /dart/disclosures` | 공시 검색 (기간, 유형, 최종보고서 필터) |
| `GET /dart/financials` | 재무제표 (BS/IS/CF, 연결/개별, 당기/전기/전전기) |
| `GET /dart/sanctions` | 제재 내역 (유형, 일자, 기관) |

### 3.3 KOFIA (펀드)

| 엔드포인트 | 설명 |
| ---- | ---- |
| `GET /kofia/funds` | 펀드 목록 (운용사, 유형 필터, 만기 경고) |
| `GET /kofia/funds/{fund_code}` | 펀드 상세 + 운용인력 목록 |
| `GET /kofia/managers` | 운용 전문인력 목록 |

주요 필드: `fund_code`, `fund_name`, `fund_type`(blind/project), `company_name`, `total_amount`, `vintage_year`, `is_maturity_alert`, `management_fee_rate`, `performance_fee_rate`

### 3.4 REITs (리츠)

| 엔드포인트 | 설명 |
| ---- | ---- |
| `GET /reits` | 리츠 목록 (유형, 상태 필터, 자산비율 경고) |
| `GET /reits/{reits_code}` | 리츠 상세 + 보유 자산 목록 |
| `GET /reits/{reits_code}/assets` | 리츠 자산 내역 |

주요 필드: `reits_code`, `reits_name`, `reits_type`(self_managed/entrusted), `total_assets`, `real_estate_ratio`, `has_asset_ratio_warning`, `dividend_rate`, `status`(authorized/operating/dissolved)

### 3.5 News (뉴스)

| 엔드포인트 | 설명 |
| ---- | ---- |
| `GET /news` | 뉴스 목록 (감성점수 포함, 페이지네이션) |

주요 필드: `title`, `source`, `published_at`, `url`, `sentiment_score`(-1.0 ~ 1.0)

---

## 4. IM Module 백엔드 현황

- API 라우트: **아직 미구현** (빈 `__init__.py`만 존재)
- 핵심 엔진 모듈은 구현됨:
  - `data_ingestor/` : DART + Playwright 크롤러
  - `financial_engine/` : 재무 정규화 + 지표 산출
  - `narrative_generator/` : LangChain RAG 내러티브
  - `chart_engine/` : Plotly 차트
  - `design_renderer/` : PPTX/PDF 조립
- **IM Module 프론트엔드 통합은 API 구축이 선행되어야 함** -> Phase 2

---

## 5. 통합 구현 계획

### Phase 1: KIIS 인텔리전스 모듈 통합 (우선)

#### Step 1-1: 인프라 — KIIS API 프록시 설정

수정 파일:
- `docker-compose.yml` : KIIS 백엔드 서비스 추가 (port 8001)
- `config/nginx/default.conf` : API 프록시 라우팅

```nginx
# Nginx 프록시 라우팅
location /api/v1/intel/ {
    proxy_pass http://kiis-backend:8001/api/v1/;
}
location /api/v1/ {
    proxy_pass http://fdd-backend:8000/api/v1/;  # 기존
}
```

기존 `frontend/src/api/client.ts`의 axios 인스턴스를 그대로 재사용 (baseURL `/api/v1`, JWT 자동 적용).

#### Step 1-2: TypeScript 타입 정의

신규 파일: `frontend/src/types/intelligence.ts`

KIIS 백엔드 Pydantic 스키마를 1:1 매핑하여 TypeScript interface로 정의한다.

```typescript
// 공통 페이지네이션
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  size: number;
  items: T[];
}

// ── 기업 (Company) ──
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

// ── 공시 (Disclosure) ──
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

// ── 재무제표 (Financial Statement) ──
export interface FinancialStatementItem {
  rcept_no: string;
  bsns_year: string;
  sj_div: string;         // BS, IS, CF 등
  sj_nm: string;
  account_id: string;
  account_nm: string;
  thstrm_nm: string;
  thstrm_amount: string;  // 금액은 string (Money Rules)
  frmtrm_nm: string;
  frmtrm_amount: string;
  bfefrmtrm_nm: string;
  bfefrmtrm_amount: string;
}

// ── 제재 (Sanction) ──
export interface SanctionItem {
  corp_code: string;
  corp_name: string;
  sanctions_type: string;
  sanctions_detail: string;
  sanctions_date: string;
  sanctions_agency: string;
}

// ── 펀드 (Fund) ──
export interface FundListItem {
  fund_code: string;
  fund_name: string;
  fund_type: string;       // blind / project
  company_name: string;
  total_amount: string | null;  // 금액 string
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

// ── 리츠 (REITs) ──
export interface REITsListItem {
  reits_code: string;
  reits_name: string;
  reits_type: string;      // self_managed / entrusted
  management_company: string;
  total_assets: string | null;
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

// ── 뉴스 (News) ──
export interface NewsListItem {
  id: number;
  title: string;
  source: string;
  author: string | null;
  published_at: string | null;
  url: string;
  sentiment_score: number | null;
}
```

**주의:** 모든 금액 필드는 `string` 타입 사용 (CLAUDE.md Money Rules: NEVER float).

#### Step 1-3: Custom Hooks

신규 파일: `frontend/src/hooks/useIntelligence.ts`

기존 `hooks/useDeals.ts` 패턴(useQuery + axios)을 따라 작성:

```typescript
// 기업
useCompanies(search?, corp_cls?, page, size) -> useQuery<PaginatedResponse<CompanyListItem>>
useCompany(corpCode) -> useQuery<CompanyInfo>

// DART
useDisclosures(params) -> useQuery<DisclosureListResponse>
useFinancials(params) -> useQuery<FinancialListResponse>
useSanctions(corpCode) -> useQuery<SanctionListResponse>

// 펀드
useFunds(company_name?, fund_type?, page, size) -> useQuery<PaginatedResponse<FundListItem>>
useFund(fundCode) -> useQuery<FundDetailResponse>

// 리츠
useREITs(reits_type?, status?, page, size) -> useQuery<PaginatedResponse<REITsListItem>>
useREITsDetail(reitsCode) -> useQuery<REITsDetailResponse>

// 뉴스
useNews(page, size) -> useQuery<PaginatedResponse<NewsListItem>>
```

API 경로 prefix: `/intel/` (Nginx에서 KIIS 백엔드로 프록시)

#### Step 1-4: 페이지 컴포넌트 (4개)

기존 재사용 컴포넌트:

| 컴포넌트 | 경로 | 용도 |
| ---- | ---- | ---- |
| DataTable | `components/ui/DataTable.tsx` | 목록 테이블 (키보드 네비게이션, Skeleton 로딩) |
| Card | `components/ui/Card.tsx` | 카드 레이아웃 |
| KpiCard | `components/ui/KpiCard.tsx` | 핵심 수치 카드 |
| Badge | `components/ui/Badge.tsx` | 상태/경고 표시 |
| Input | `components/ui/Input.tsx` | 검색 입력 |
| Select | `components/ui/Select.tsx` | 필터 드롭다운 |
| Modal | `components/ui/Modal.tsx` | 상세 팝업 |
| Skeleton | `components/ui/Skeleton.tsx` | 로딩 상태 |
| EmptyState | `components/ui/EmptyState.tsx` | 빈 데이터 |
| FinancialBarChart | `components/charts/FinancialBarChart.tsx` | 재무 바 차트 |
| TrendLineChart | `components/charts/TrendLineChart.tsx` | 트렌드 라인 차트 |

**(a) IntelligenceDashboardPage.tsx** (대시보드)
- 기업 검색 바 (Input)
- KpiCard 행: 전체 기업 수, 활성 펀드 수, 운영 리츠 수, 뉴스 건수
- 최근 뉴스 카드 (감성 점수 컬러 코딩: 양수=초록, 음수=빨강)
- 만기 임박 펀드 경고 리스트 (is_maturity_alert=true)
- 자산비율 미달 리츠 경고 리스트 (has_asset_ratio_warning=true)

**(b) CompanySearchPage.tsx** (기업 검색/목록)
- 검색 Input + 법인구분 Select (유가/코스닥/코넥스/기타)
- DataTable: corp_name, stock_code, corp_cls, modify_date
- 행 클릭 -> 상세 (공시/재무/제재 탭)
- 재무제표 탭에서 FinancialBarChart 활용

**(c) FundListPage.tsx** (펀드 목록)
- 운용사 검색 Input + 유형 Select (블라인드/프로젝트)
- DataTable: fund_name, company_name, fund_type, total_amount, vintage_year
- 만기 경고 Badge (is_maturity_alert)
- 행 클릭 -> Modal (펀드 상세 + 운용인력 DataTable)

**(d) ReitsListPage.tsx** (리츠 목록)
- 유형 Select (자기관리/위탁관리) + 상태 Select (인가/영업/해산)
- DataTable: reits_name, reits_type, management_company, total_assets, real_estate_ratio, status
- 자산비율 경고 Badge (has_asset_ratio_warning)
- 행 클릭 -> Modal (리츠 상세 + 보유 자산 DataTable)

#### Step 1-5: 사이드바 & 라우팅 확장

수정 파일:
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/App.tsx`

Sidebar에 Intelligence 섹션 추가:

```
기존:
  Deals                    (Briefcase)

추가:
  Intelligence (섹션 헤더)
  ├── Dashboard            (BarChart3)
  ├── Companies            (Building2)
  ├── Funds                (Wallet)
  └── REITs                (Building)
```

App.tsx 라우트 추가:

```
/intelligence              -> IntelligenceDashboardPage
/intelligence/companies    -> CompanySearchPage
/intelligence/funds        -> FundListPage
/intelligence/reits        -> ReitsListPage
```

---

### Phase 2: IM Module 통합 (KIIS 완료 후)

> IM Module은 API가 아직 미구현이므로 백엔드 API 구축이 선행되어야 한다.

#### Step 2-1: IM Module API 구축 (백엔드 선행 작업)

| 엔드포인트 | 설명 |
| ---- | ---- |
| `POST /im/projects` | IM 프로젝트 생성 |
| `GET /im/projects` | IM 프로젝트 목록 |
| `POST /im/projects/{id}/collect` | 데이터 수집 (DART + 크롤링) |
| `POST /im/projects/{id}/analyze` | 재무 분석 실행 |
| `POST /im/projects/{id}/generate` | IM 문서 생성 |
| `GET /im/projects/{id}/status` | 진행 상태 (Celery task status) |
| `GET /im/projects/{id}/download` | 생성된 PPTX/PDF 다운로드 |

#### Step 2-2: 프론트엔드 확장

| 파일 | 설명 |
| ---- | ---- |
| `types/im.ts` | IM 프로젝트/상태 타입 정의 |
| `hooks/useImGenerator.ts` | IM API 호출 hooks |
| `pages/ImProjectListPage.tsx` | IM 프로젝트 목록 |
| `pages/ImGeneratorPage.tsx` | IM 생성 위저드 |

IM 생성 위저드 단계:
1. 기업 선택 (KIIS CompanySearch 컴포넌트 재사용)
2. 데이터 수집 진행률 표시 (Celery task polling)
3. 섹션별 내러티브 미리보기/편집 (14개 섹션)
4. 문서 생성 & PPTX/PDF 다운로드

---

## 6. 파일 변경 요약

### Phase 1 신규 생성 파일

| 파일 | 설명 |
| ---- | ---- |
| `frontend/src/types/intelligence.ts` | KIIS API TypeScript 타입 정의 |
| `frontend/src/hooks/useIntelligence.ts` | KIIS API TanStack Query hooks |
| `frontend/src/pages/IntelligenceDashboardPage.tsx` | 인텔리전스 대시보드 |
| `frontend/src/pages/CompanySearchPage.tsx` | 기업 검색/목록/상세 |
| `frontend/src/pages/FundListPage.tsx` | 펀드 목록/상세 |
| `frontend/src/pages/ReitsListPage.tsx` | 리츠 목록/상세 |

### Phase 1 수정 파일

| 파일 | 변경 내용 |
| ---- | ---- |
| `frontend/src/App.tsx` | `/intelligence/*` 라우트 추가 |
| `frontend/src/components/layout/Sidebar.tsx` | Intelligence 네비게이션 섹션 추가 |
| `docker-compose.yml` | KIIS 백엔드 서비스 추가 (선택) |
| `config/nginx/default.conf` | `/api/v1/intel/` 프록시 추가 (선택) |

### 수정 불필요 — 재사용 컴포넌트

| 컴포넌트 | 경로 |
| ---- | ---- |
| DataTable | `frontend/src/components/ui/DataTable.tsx` |
| Card | `frontend/src/components/ui/Card.tsx` |
| KpiCard | `frontend/src/components/ui/KpiCard.tsx` |
| Badge | `frontend/src/components/ui/Badge.tsx` |
| Input | `frontend/src/components/ui/Input.tsx` |
| Select | `frontend/src/components/ui/Select.tsx` |
| Modal | `frontend/src/components/ui/Modal.tsx` |
| Skeleton | `frontend/src/components/ui/Skeleton.tsx` |
| EmptyState | `frontend/src/components/ui/EmptyState.tsx` |
| FinancialBarChart | `frontend/src/components/charts/FinancialBarChart.tsx` |
| TrendLineChart | `frontend/src/components/charts/TrendLineChart.tsx` |
| api/client.ts | `frontend/src/api/client.ts` |

---

## 7. 검증 방법

1. **빌드**: `cd frontend && npm run build` — 타입 에러 없이 성공
2. **린트**: `cd frontend && npm run lint` — 0 warnings
3. **UI 동작**:
   - `/intelligence` 대시보드 렌더링
   - `/intelligence/companies` 검색/필터/페이지네이션
   - `/intelligence/funds` 펀드 목록/만기 경고 Badge
   - `/intelligence/reits` 리츠 목록/자산비율 경고 Badge
4. **접근성**: 사이드바/DataTable 키보드 네비게이션
5. **회귀**: 기존 `/deals` 페이지 정상 동작 확인
