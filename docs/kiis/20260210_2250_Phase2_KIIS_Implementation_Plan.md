# Phase 2: KIIS Module 구현 계획

## Context

KIIS(Korea Investment Intelligence System)는 한국 투자 정보 통합 플랫폼의 프론트엔드 모듈이다. DART(금감원), KOFIA(금투협), REITs(국토부), 뉴스 등 다양한 데이터 소스를 통합하여 투자 인텔리전스를 제공한다.

**현재 상태:** `src/modules/kiis/KiisRoutes.tsx`에 placeholder만 존재. `kiisApi` 클라이언트, Vite 프록시, 사이드바 네비게이션은 이미 구성됨.

**목표:** 8개 페이지(Dashboard, Companies, Funds, REITs, News, Deals, Sanctions, Watchlist)와 관련 상세 페이지를 FDD 모듈 패턴에 맞춰 구현.

**결정 사항:**

- 추가 기능(Entity Resolution, Portfolio, Manager 이동)은 관련 페이지에 하위 섹션으로 통합
- 인증은 기존 공유 auth 유지 (FDD auth 토큰을 KIIS API에도 사용)

---

## 파일 구조

```text
src/modules/kiis/
├── KiisRoutes.tsx                    # 라우트 정의
├── types/
│   ├── company.ts                    # Company, DART financial 타입
│   ├── fund.ts                       # Fund, Manager 타입
│   ├── reit.ts                       # REIT, Asset 타입
│   ├── news.ts                       # News article 타입
│   ├── deal.ts                       # Deal, DealAggregation 타입
│   ├── sanction.ts                   # Sanction, classification 타입
│   ├── watchlist.ts                  # Watchlist, Alert 타입
│   ├── dashboard.ts                  # Dashboard summary 타입
│   ├── analysis.ts                   # Reputation score 타입
│   └── search.ts                     # Unified search 타입
├── hooks/
│   ├── useDashboard.ts               # Dashboard summary
│   ├── useCompanies.ts               # Companies + DART + financials + disclosures
│   ├── useFunds.ts                   # Funds + managers (KOFIA)
│   ├── useReits.ts                   # REITs + assets
│   ├── useNews.ts                    # News articles + collection
│   ├── useDeals.ts                   # Deals + aggregations + trends
│   ├── useSanctions.ts               # Sanctions + classification
│   ├── useWatchlist.ts               # Watchlist + alerts
│   ├── useAnalysis.ts                # Reputation scores
│   └── useSearch.ts                  # Unified search
├── pages/
│   ├── DashboardPage.tsx             # /kiis
│   ├── CompanyListPage.tsx           # /kiis/companies
│   ├── CompanyDetailPage.tsx         # /kiis/companies/:corpCode
│   ├── FundListPage.tsx              # /kiis/funds
│   ├── FundDetailPage.tsx            # /kiis/funds/:fundCode
│   ├── ReitListPage.tsx              # /kiis/reits
│   ├── ReitDetailPage.tsx            # /kiis/reits/:reitsCode
│   ├── NewsListPage.tsx              # /kiis/news
│   ├── NewsDetailPage.tsx            # /kiis/news/:articleId
│   ├── DealSourcingPage.tsx          # /kiis/deals
│   ├── SanctionListPage.tsx          # /kiis/sanctions
│   └── WatchlistPage.tsx             # /kiis/watchlist
└── components/
    ├── ReputationBadge.tsx           # 평판 점수 시각화 뱃지
    ├── CompanyFinancials.tsx          # 재무제표 테이블/차트 섹션
    ├── DealTrendChart.tsx            # 딜 트렌드 차트 래퍼
    ├── SentimentIndicator.tsx        # 뉴스 감성 분석 표시
    └── SearchBar.tsx                 # 통합 검색 바 (Dashboard 헤더)
```

---

## Step 1: Types 정의 + KiisRoutes 라우팅

### 라우트 구조 (`KiisRoutes.tsx`)

| 경로 | 페이지 |
| --- | --- |
| `/kiis` (index) | DashboardPage |
| `/kiis/companies` | CompanyListPage |
| `/kiis/companies/:corpCode` | CompanyDetailPage |
| `/kiis/funds` | FundListPage |
| `/kiis/funds/:fundCode` | FundDetailPage |
| `/kiis/reits` | ReitListPage |
| `/kiis/reits/:reitsCode` | ReitDetailPage |
| `/kiis/news` | NewsListPage |
| `/kiis/news/:articleId` | NewsDetailPage |
| `/kiis/deals` | DealSourcingPage |
| `/kiis/sanctions` | SanctionListPage |
| `/kiis/watchlist` | WatchlistPage |

### Types 정의

**`company.ts`**

- `Company` - corp_code, corp_name, stock_code, corp_cls, ceo_nm, address 등
- `CompanyDetail` - Company 확장 + industry, est_dt, homepage 등
- `FinancialStatement` - account_nm, thstrm_amount, frmtrm_amount, bfefrmtrm_amount
- `Disclosure` - rcept_no, report_nm, rcept_dt, flr_nm, viewer_url, pdf_url
- `PaginatedResponse<T>` - items, total, page, size

**`fund.ts`**

- `Fund` - fund_code, fund_name, fund_type, total_amount, mgmt_fee_rate, vintage_year, is_maturity_alert
- `FundDetail` - Fund + managers
- `FundManager` - name, position, role, career_years, education, certifications, is_active

**`reit.ts`**

- `Reit` - reits_code, name, type (self_managed/entrusted), status, management_company
- `ReitAsset` - asset_name, asset_type, valuation, ratio

**`news.ts`**

- `NewsArticle` - id, title, content, source, published_at, company associations, sentiment

**`deal.ts`**

- `Deal` - investor_name, target_company, amount, round_stage, sector, deal_date, is_lead
- `DealBySector` / `DealByStage` - aggregation 타입
- `DealTrend` - year, count, total_amount

**`sanction.ts`**

- `ClassifiedSanction` - sanction_type, detail, agency, date, severity, reasoning, category
- `SanctionSummary` - caution_count, warning_count, critical_count

**`analysis.ts`**

- `ReputationScore` - corp_code, total_score, trend_score, news_score, performance_score, status_tag

**`watchlist.ts`**

- `WatchlistItem` - id, company_id, corp_code, corp_name, alert_types, added_at
- `Alert` - id, type, message, company_name, created_at, is_read

**`dashboard.ts`**

- `DashboardSummary` - total_companies, total_funds, total_reits, total_news, total_deals, news_last_7days, recent_deals[], risk_companies[]

**`search.ts`**

- `SearchResult` - type, id, name, description, score

---

## Step 2: Hooks 구현

모든 hook은 `kiisApi`(`src/api/kiisClient.ts`)를 import하고 FDD 패턴(useQuery/useMutation)을 따름.

### `useDashboard.ts`

- `useDashboardSummary()` → GET `/dashboard/summary`

### `useCompanies.ts`

- `useCompanies(params)` → GET `/companies` (search, corp_cls, page, size)
- `useCompanyDetail(corpCode)` → GET `/companies/{corpCode}`
- `useCompanyFinancials(corpCode, params)` → GET `/dart/companies/{corpCode}/financials`
- `useCompanyDisclosures(corpCode)` → GET `/disclosures/{corpCode}`
- `useDisclosureLink(rceptNo)` → GET `/disclosures/link/{rceptNo}`
- `useSyncDisclosures(corpCode)` → POST mutation `/disclosures/{corpCode}/sync`
- `useReputationScore(corpCode)` → GET `/analysis/reputation/{corpCode}`
- `useReputationHistory(corpCode)` → GET `/analysis/reputation/{corpCode}/history`

### `useFunds.ts`

- `useFunds(params)` → GET `/kofia/funds` (company_name, fund_type, page, size)
- `useFundDetail(fundCode)` → GET `/kofia/funds/{fundCode}`
- `useFundManagers(params)` → GET `/kofia/managers`

### `useReits.ts`

- `useReits(params)` → GET `/reits` (type, status, page, size)
- `useReitDetail(reitsCode)` → GET `/reits/{reitsCode}`
- `useReitAssets(reitsCode)` → GET `/reits/{reitsCode}/assets`

### `useNews.ts`

- `useNewsList(params)` → GET `/news` (source, date range, company_id, page, size)
- `useNewsDetail(articleId)` → GET `/news/{articleId}`
- `useCollectNews()` → POST mutation `/news/collect`

### `useDeals.ts`

- `useDealsByCompany(corpCode)` → GET `/deals/by-company/{corpCode}`
- `useDealsBySector(params)` → GET `/deals/by-sector`
- `useDealsByStage(params)` → GET `/deals/by-stage`
- `useDealTrends(params)` → GET `/deals/trends`

### `useSanctions.ts`

- `useClassifiedSanctions(corpCode)` → GET `/sanctions/classified/{corpCode}`
- `useSanctionSummary(corpCode)` → GET `/sanctions/classified/{corpCode}/summary`
- `useClassifySanctions(corpCode)` → POST mutation `/sanctions/classify/{corpCode}`

### `useWatchlist.ts`

- `useWatchlist()` → GET `/watchlist`
- `useAddToWatchlist()` → POST mutation `/watchlist`
- `useRemoveFromWatchlist()` → DELETE mutation `/watchlist/{companyId}`
- `useAlerts()` → GET `/alerts`
- `useMarkAlertRead()` → POST mutation `/alerts/{alertId}/read`
- `useUnreadAlertCount()` → GET `/alerts/unread-count`

### `useSearch.ts`

- `useUnifiedSearch(params)` → GET `/search` (q, type, page, size)

### `useAnalysis.ts`

- `useReputationList(params)` → GET `/analysis/reputation`
- `useCalculateReputation(corpCode)` → POST mutation `/analysis/reputation/{corpCode}/calculate`

---

## Step 3: Dashboard 페이지

### DashboardPage (`/kiis`)

- **SearchBar**: 통합 검색 (useSearch 연동, 결과 드롭다운으로 해당 엔티티 페이지로 이동)
- **KPI Cards (4개)**:
  - 등록 기업 수 (total_companies)
  - 등록 펀드 수 (total_funds)
  - 최근 7일 뉴스 수 (news_last_7days)
  - 총 딜 수 (total_deals)
- **최근 딜** 섹션: DataTable (recent_deals - 투자자, 대상, 금액, 라운드, 날짜)
- **리스크 기업** 섹션: DataTable (risk_companies - 기업명, 평판 점수, 상태 태그)

---

## Step 4: Companies 페이지

### CompanyListPage (`/kiis/companies`)

- **필터**: 검색 (Input), 법인구분 필터 (Select: 상장/코스닥/코넥스/기타)
- **DataTable 컬럼**: 기업명, 종목코드, 법인구분(Badge), CEO, 업종
- **행 클릭**: `/kiis/companies/:corpCode`로 이동
- **페이지네이션**: page, size 파라미터

### CompanyDetailPage (`/kiis/companies/:corpCode`)

- **기업 헤더**: 기업명, 종목코드, CEO, 주소, 홈페이지 링크
- **평판 점수 카드**: ReputationBadge (total_score, status_tag), 점수 breakdown
- **탭 또는 섹션**:
  1. **재무제표** (CompanyFinancials 컴포넌트): 사업연도/보고서유형 Select → FinancialBarChart + DataTable
  2. **공시** 섹션: DataTable (보고서명, 접수일, 제출인) + 열람 링크
  3. **관련 딜** 섹션: useDealsByCompany 연동
  4. **제재** 섹션: useClassifiedSanctions 연동 (severity Badge)
- **워치리스트 추가** 버튼

---

## Step 5: Funds 페이지

### FundListPage (`/kiis/funds`)

- **필터**: 운용사명 검색 (Input), 펀드유형 (Select: blind/project)
- **DataTable 컬럼**: 펀드명, 유형(Badge), 운용사, 설정총액, 운용보수, 성과보수, 빈티지, 만기알림(Badge)
- **행 클릭**: `/kiis/funds/:fundCode`
- **페이지네이션**

### FundDetailPage (`/kiis/funds/:fundCode`)

- **펀드 헤더**: 펀드명, 유형, 운용사, 설정총액
- **KPI Cards**: 설정총액, 운용보수율, 성과보수율, 빈티지연도
- **매니저** 섹션: DataTable (이름, 직위, 역할, 경력연수, 학력, 자격증, 활동상태 Badge)

---

## Step 6: REITs + News 페이지

### ReitListPage (`/kiis/reits`)

- **필터**: 유형 (Select: self_managed/entrusted), 상태 (Select: authorized/operating/dissolved)
- **DataTable 컬럼**: REITs명, 유형(Badge), 상태(Badge), 운용사
- **행 클릭**: `/kiis/reits/:reitsCode`

### ReitDetailPage (`/kiis/reits/:reitsCode`)

- **REITs 헤더**: 이름, 유형, 상태, 운용사
- **자산 목록**: DataTable (자산명, 자산유형, 감정가, 비율)

### NewsListPage (`/kiis/news`)

- **필터**: 소스 (Select: platum/dealsite), 날짜 범위 (Input: date), 검색어
- **뉴스 수집** 버튼 (POST /news/collect, Admin 전용)
- **Card 기반 목록**: 제목, 소스 Badge, 날짜, 감성 분석 SentimentIndicator
- **클릭**: `/kiis/news/:articleId`

### NewsDetailPage (`/kiis/news/:articleId`)

- **기사 헤더**: 제목, 소스, 날짜
- **본문** 표시
- **감성 분석 결과**: SentimentIndicator
- **관련 기업** 링크

---

## Step 7: Deals + Sanctions + Watchlist 페이지

### DealSourcingPage (`/kiis/deals`)

- **탭 기반 레이아웃**:
  1. **트렌드 탭**: TrendLineChart (연도별 딜 수 + 금액), useDealTrends
  2. **섹터별 탭**: DataTable (섹터, 딜수, 총 금액), useDealsBySector
  3. **스테이지별 탭**: DataTable (라운드, 딜수, 총 금액), useDealsByStage
- **필터**: years lookback (Select: 1~10년)

### SanctionListPage (`/kiis/sanctions`)

- **검색**: 기업 코드/이름 입력 → 검색
- **제재 요약** KPI Cards: 주의(caution), 경고(warning), 위험(critical) 건수
- **DataTable 컬럼**: 기업명, 제재유형, 제재기관, 일자, 심각도(Badge), 카테고리
- **분류 실행** 버튼 (POST classify, 특정 기업 선택 후)

### WatchlistPage (`/kiis/watchlist`)

- **2-섹션 레이아웃**:
  1. **워치리스트**: DataTable (기업명, 알림유형 Badges, 추가일, 삭제 버튼)
  2. **알림 히스토리**: DataTable (유형 Badge, 메시지, 기업명, 날짜, 읽음여부)
     - 읽지 않은 알림 수 Badge 표시
     - 클릭 시 읽음 처리

---

## Step 8: 공통 컴포넌트

### ReputationBadge

- 점수 범위별 색상 (0-40: red, 40-60: yellow, 60-80: blue, 80-100: green)
- status_tag(rising/stable/risk) 표시

### CompanyFinancials

- 사업연도/보고서유형 셀렉터
- FinancialBarChart (당기/전기/전전기 비교)
- DataTable (계정명, 당기, 전기, 전전기 금액)

### DealTrendChart

- TrendLineChart 래퍼 (연도, 딜 수, 금액 dual axis)

### SentimentIndicator

- 감성 점수 시각화 (positive/neutral/negative Badge)

### SearchBar

- Input + 디바운스 검색 + 결과 드롭다운
- 엔티티 타입별 아이콘 + 이름 표시
- 클릭 시 해당 상세 페이지 이동

---

## 구현 순서

| 순서 | 내용 | 파일 수 | 의존성 |
| --- | --- | --- | --- |
| **1** | Types 전체 + KiisRoutes | ~11 | 없음 |
| **2** | Hooks 전체 | ~10 | Types |
| **3** | DashboardPage + SearchBar | 2 | Hooks |
| **4** | CompanyListPage + CompanyDetailPage + CompanyFinancials + ReputationBadge | 4 | Hooks |
| **5** | FundListPage + FundDetailPage | 2 | Hooks |
| **6** | ReitListPage + ReitDetailPage | 2 | Hooks |
| **7** | NewsListPage + NewsDetailPage + SentimentIndicator | 3 | Hooks |
| **8** | DealSourcingPage + DealTrendChart | 2 | Hooks |
| **9** | SanctionListPage | 1 | Hooks |
| **10** | WatchlistPage | 1 | Hooks |

---

## 재사용할 기존 리소스

| 리소스 | 경로 | 용도 |
| --- | --- | --- |
| `kiisApi` | `src/api/kiisClient.ts` | 모든 hook에서 import |
| `createApiClient` | `src/api/client.ts` | 이미 사용 중 |
| UI 컴포넌트 | `src/components/ui/` | Button, Card, KpiCard, DataTable, Badge, Modal, Input, Select, Spinner, EmptyState, Skeleton |
| Layout | `src/components/layout/` | PageHeader, AppShell (이미 적용됨) |
| Charts | `src/components/charts/` | TrendLineChart, FinancialBarChart |
| Utilities | `src/lib/` | cn(), formatAmount(), formatDate(), formatPercent(), formatCompact() |
| Auth | `src/hooks/useAuth.ts` | hasPermission() for Admin-only 기능 |
| Sidebar Nav | `src/components/layout/Sidebar.tsx` | KIIS_NAV 이미 정의됨 |

---

## 검증 방법

1. `npm run dev`로 개발 서버 실행
2. `/kiis`로 접속하여 Dashboard 확인
3. 사이드바의 각 네비게이션 항목을 클릭하여 모든 페이지 로드 확인
4. KIIS 백엔드(`:8001`)가 실행 중인 경우 실제 데이터 확인
5. 백엔드 미실행 시 로딩/에러 상태가 적절히 표시되는지 확인
6. `npm run build`로 빌드 에러 없음 확인
7. 반응형: 모바일 뷰에서 레이아웃 확인
