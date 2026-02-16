# AMIC Platform - 프론트엔드 통합 계획서

## 1. 개요

KIIS(투자 인텔리전스), Auto FDD(재무 실사), IM Module(투자설명서 생성) 세 프로젝트를 **AMIC Platform**이라는 하나의 프론트엔드로 통합한다. Auto FDD의 프론트엔드(React 19 + TS + Vite)를 확장하여 KIIS와 IM Module 기능을 추가한다. 백엔드는 각각 독립 서버로 운영한다.

---

## 2. 프론트엔드 비교 평가

| 프로젝트 | 프론트엔드 | 점수 | 비고 |
| --- | --- | --- | --- |
| **Auto FDD** | React 19 + TS + Vite + Tailwind (10,227줄, 33컴포넌트, 15페이지) | **85/100** | 프로덕션 수준 |
| **KIIS** | 없음 (백엔드 API만 존재) | **0/100** | Swagger UI만 존재 |
| **IM Module** | 없음 (Python 문서생성 파이프라인) | **0/100** | API 레이어 미구현 |

### Auto FDD 프론트엔드 상세

| 항목 | 상세 |
| --- | --- |
| **프레임워크** | React 19 + TypeScript 5.7 + Vite 6.0 |
| **코드량** | ~10,227 lines TSX/TS |
| **페이지** | 15개 (Login, Deal List, Workspace, QoE, NWC, Report 등) |
| **컴포넌트** | 33개 재사용 가능 UI 컴포넌트 |
| **커스텀 훅** | 11개 (useDeals, useAuth, useQoE 등) |
| **상태관리** | TanStack Query 5 + React Context |
| **스타일링** | Tailwind CSS 3.4 (AMIC 브랜드 커스텀 테마) |
| **인증** | JWT + 자동 리프레시 토큰 |
| **접근성** | 키보드 네비게이션, ARIA 라벨, 반응형 |
| **배포** | Docker + nginx 멀티스테이지 빌드 |
| **코드 품질** | ESLint strict, no `any`, Prettier |

**결론:** Auto FDD의 프론트엔드가 유일하며 압도적으로 우월하므로 이를 확장하여 통합 플랫폼을 구축한다.

---

## 3. 현재 상태 요약

| 프로젝트 | 프론트엔드 | 백엔드 | 포트 |
| --- | --- | --- | --- |
| **Auto FDD** | React 19 (10,227줄, 15페이지, 33컴포넌트) | FastAPI 완성 (17 라우터) | :8000 |
| **KIIS** | 없음 | FastAPI 완성 (15 라우터, 100+ 엔드포인트) | :8001 |
| **IM Module** | 없음 | FastAPI 미완성 (API 레이어 미구현) | :8002 |

---

## 4. 아키텍처

```
┌─────────────────────────────────────────────────┐
│           AMIC Platform (React SPA)              │
│         localhost:5173 (dev) / nginx (prod)       │
├─────────────────────────────────────────────────┤
│  /api/fdd/*  │  /api/kiis/*  │  /api/im/*       │
│      ↓       │      ↓        │      ↓            │
│  Vite Proxy  │  Vite Proxy   │  Vite Proxy       │
└──────┬───────┴──────┬────────┴──────┬────────────┘
       ↓              ↓               ↓
  Auto FDD        KIIS Backend    IM Module
  :8000            :8001            :8002
  (PostgreSQL)     (PostgreSQL      (PostgreSQL
                   +Redis+ES)       +Redis+Celery)
```

---

## 5. 구현 계획

### Phase 1: 프론트엔드 기반 리브랜딩 + 멀티백엔드 설정

#### 1-1. 프로젝트 복사 및 리브랜딩

- `Auto FDD_backup/frontend/` → 새 위치에 `amic-platform/` 복사
- `package.json` name을 `amic-platform`으로 변경
- 사이드바 로고/타이틀을 "AMIC Platform"으로 변경

#### 1-2. Vite 프록시 설정 (멀티 백엔드)

**수정 파일:** `vite.config.ts`

```typescript
proxy: {
  "/api/fdd": {
    target: "http://localhost:8000",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/fdd/, "/api/v1"),
  },
  "/api/kiis": {
    target: "http://localhost:8001",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/kiis/, "/api/v1"),
  },
  "/api/im": {
    target: "http://localhost:8002",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/im/, "/api/v1"),
  },
}
```

#### 1-3. API 클라이언트 분리

**새 파일:** `src/api/clients.ts`

```typescript
// 기존 client.ts의 인터셉터 로직을 공유하면서 3개 인스턴스 생성
export const fddApi = createApiClient("/api/fdd");   // Auto FDD
export const kiisApi = createApiClient("/api/kiis");  // KIIS
export const imApi = createApiClient("/api/im");      // IM Module
```

- JWT 인터셉터(토큰 첨부 + 자동 리프레시)를 공통 함수로 추출
- 3개 axios 인스턴스에 동일 인터셉터 적용
- 기존 `client.ts`의 `api`는 `fddApi`로 alias하여 기존 훅 호환 유지

#### 1-4. 인증 통합 전략

- **1차**: Auto FDD의 JWT 인증을 기본으로 사용 (기존 LoginPage 유지)
- KIIS/IM 백엔드는 개발 중 `AUTH_ENABLED=False`로 운영
- **2차 (추후)**: 통합 인증 서버(Auth Server) 또는 각 백엔드에 동일 JWT_SECRET 공유

---

### Phase 2: 사이드바 네비게이션 확장

**수정 파일:** `src/components/layout/Sidebar.tsx`

```
AMIC Platform
├── FDD (Financial Due Diligence)        ← 기존 Auto FDD
│   ├── Deals
│   └── (deal workspace: setup, VDR, QoE, NWC, ...)
│
├── KIIS (Investment Intelligence)       ← 신규
│   ├── Dashboard (대시보드)
│   ├── Companies (기업 탐색)
│   ├── Funds (펀드 정보)
│   ├── REITs (리츠)
│   ├── News & Sentiment (뉴스/감성)
│   ├── Reputation (평판 분석)
│   ├── Deals (딜 소싱)
│   ├── Sanctions (제재 모니터링)
│   └── Watchlist (관심 종목)
│
├── IM Generator                          ← 신규
│   ├── Projects (IM 프로젝트 목록)
│   ├── New IM (새 IM 생성 위저드)
│   └── Templates (템플릿 관리)
│
└── Settings
    └── Profile / Logout
```

---

### Phase 3: KIIS 프론트엔드 페이지 구현

#### 3-1. 새로 만들 페이지 (9개)

| 페이지 | 경로 | KIIS API | 재사용 컴포넌트 |
| --- | --- | --- | --- |
| **Dashboard** | `/kiis` | `/dashboard/summary` | KpiCard, charts |
| **Company List** | `/kiis/companies` | `/companies`, `/search` | DataTable, Input |
| **Company Detail** | `/kiis/companies/:corpCode` | `/companies/{corp_code}`, `/analysis/reputation/{corp_code}` | Card, Badge, charts |
| **Fund List** | `/kiis/funds` | `/kofia/funds` | DataTable |
| **Fund Detail** | `/kiis/funds/:fundCode` | `/kofia/funds/{fund_code}` | Card |
| **News Feed** | `/kiis/news` | `/news/articles`, `/news/sentiment` | DataTable, Badge |
| **Deal Sourcing** | `/kiis/deals` | `/deals/by-sector`, `/deals/by-stage`, `/deals/trends` | Charts (Bar, Trend) |
| **Sanctions** | `/kiis/sanctions` | `/sanctions` | DataTable, Badge |
| **Watchlist** | `/kiis/watchlist` | `/watchlist`, `/alerts` | DataTable, Modal |

#### 3-2. 새로 만들 훅 (9개)

| 훅 | API 클라이언트 | 주요 엔드포인트 |
| --- | --- | --- |
| `useKiisDashboard` | `kiisApi` | GET `/dashboard/summary` |
| `useCompanies` | `kiisApi` | GET `/companies`, GET `/search` |
| `useCompanyDetail` | `kiisApi` | GET `/companies/{corp_code}` |
| `useFunds` | `kiisApi` | GET `/kofia/funds` |
| `useNews` | `kiisApi` | GET `/news/articles` |
| `useReputation` | `kiisApi` | GET `/analysis/reputation/{corp_code}` |
| `useKiisDeals` | `kiisApi` | GET `/deals/by-sector`, `/deals/trends` |
| `useSanctions` | `kiisApi` | GET `/sanctions` |
| `useWatchlist` | `kiisApi` | GET/POST/DELETE `/watchlist` |

#### 3-3. 새로 만들 타입 (4개)

| 파일 | 내용 |
| --- | --- |
| `types/kiis/company.ts` | Company, CompanyDetail, ReputationScore |
| `types/kiis/fund.ts` | Fund, FundManager |
| `types/kiis/news.ts` | NewsArticle, SentimentScore |
| `types/kiis/deal.ts` | DealSourcing, SectorData, StageData |

#### 3-4. 새 컴포넌트 (KIIS 전용, 3개)

| 컴포넌트 | 용도 | 기반 |
| --- | --- | --- |
| `ReputationBadge` | Rising/Stable/Risk 상태 표시 | 기존 Badge 확장 |
| `SentimentIndicator` | 감성 점수 -1.0~+1.0 시각화 | 신규 |
| `CompanySearchBar` | ElasticSearch 기반 통합 검색 | 기존 Input 확장 |

---

### Phase 4: IM Module 프론트엔드 페이지 구현

#### 4-1. 새로 만들 페이지 (4개)

| 페이지 | 경로 | IM API | 재사용 컴포넌트 |
| --- | --- | --- | --- |
| **Project List** | `/im` | GET `/documents` | DataTable, Badge, KpiCard |
| **New IM Wizard** | `/im/new` | POST `/documents` | DealSetupWizard 패턴 참고 |
| **IM Detail/Progress** | `/im/:docId` | GET `/documents/{id}` | Card, WorkflowStepper |
| **Template Manager** | `/im/templates` | GET/POST `/templates` | DataTable, Modal |

#### 4-2. 새로 만들 훅 (3개)

| 훅 | API 클라이언트 | 주요 엔드포인트 |
| --- | --- | --- |
| `useIMDocuments` | `imApi` | GET/POST `/documents` |
| `useIMDocument` | `imApi` | GET `/documents/{id}`, GET `/documents/{id}/download` |
| `useIMTemplates` | `imApi` | GET/POST `/templates` |

#### 4-3. 새 컴포넌트 (IM 전용, 2개)

| 컴포넌트 | 용도 |
| --- | --- |
| `IMProgressTracker` | Celery 작업 진행률 표시 (polling/SSE) |
| `IMPreview` | 생성된 PPTX/PDF 미리보기 |

---

### Phase 5: 라우팅 통합

**수정 파일:** `src/App.tsx`

```typescript
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
    {/* FDD (기존) */}
    <Route index element={<Navigate to="/fdd/deals" />} />
    <Route path="fdd/deals" element={<DealListPage />} />
    <Route path="fdd/deals/new" element={<DealSetupWizardPage />} />
    <Route path="fdd/deals/:dealId/*" element={<DealWorkspacePage />} />

    {/* KIIS (신규) */}
    <Route path="kiis" element={<KiisDashboardPage />} />
    <Route path="kiis/companies" element={<CompanyListPage />} />
    <Route path="kiis/companies/:corpCode" element={<CompanyDetailPage />} />
    <Route path="kiis/funds" element={<FundListPage />} />
    <Route path="kiis/funds/:fundCode" element={<FundDetailPage />} />
    <Route path="kiis/news" element={<NewsFeedPage />} />
    <Route path="kiis/deals" element={<DealSourcingPage />} />
    <Route path="kiis/sanctions" element={<SanctionsPage />} />
    <Route path="kiis/watchlist" element={<WatchlistPage />} />

    {/* IM Generator (신규) */}
    <Route path="im" element={<IMProjectListPage />} />
    <Route path="im/new" element={<IMWizardPage />} />
    <Route path="im/:docId" element={<IMDetailPage />} />
    <Route path="im/templates" element={<IMTemplatePage />} />
  </Route>
</Routes>
```

기존 FDD 경로를 `/deals` → `/fdd/deals`로 변경 (리다이렉트 설정).

---

## 6. 구현 순서

| 순서 | 작업 | 의존성 | 병렬 가능 |
| --- | --- | --- | --- |
| **1** | Phase 1: 리브랜딩 + 멀티백엔드 프록시 + API 클라이언트 분리 | 없음 | - |
| **2** | Phase 2: 사이드바 네비게이션 확장 | Phase 1 | - |
| **3a** | Phase 3: KIIS 타입 + 훅 + 페이지 | Phase 2 | 병렬 |
| **3b** | Phase 4: IM 타입 + 훅 + 페이지 | Phase 2 | 병렬 |
| **4** | Phase 5: 라우팅 통합 + 테스트 | 3a, 3b | - |

> Phase 3과 Phase 4는 서로 독립적이므로 병렬로 진행 가능.

---

## 7. 프로덕션 배포 (nginx)

```nginx
# nginx.conf (프로덕션)
server {
    listen 80;

    location /api/fdd/ {
        proxy_pass http://fdd-backend:8000/api/v1/;
    }
    location /api/kiis/ {
        proxy_pass http://kiis-backend:8001/api/v1/;
    }
    location /api/im/ {
        proxy_pass http://im-backend:8002/api/v1/;
    }
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;  # SPA fallback
    }
}
```

---

## 8. 파일 생성/수정 목록

### 수정 (기존 파일, 6개)

| 파일 | 변경 내용 |
| --- | --- |
| `package.json` | name → "amic-platform" |
| `vite.config.ts` | 3개 백엔드 프록시 추가 |
| `src/api/client.ts` | 인터셉터 로직 공통 함수로 추출 |
| `src/App.tsx` | KIIS/IM 라우트 추가, FDD 경로 변경 |
| `src/components/layout/Sidebar.tsx` | 3섹션 네비게이션 |
| `src/components/layout/AppShell.tsx` | 타이틀 "AMIC Platform" |

### 신규 (새 파일, ~28개)

| 카테고리 | 파일 | 개수 |
| --- | --- | --- |
| API | `src/api/clients.ts` | 1 |
| Types | `src/types/kiis/*.ts`, `src/types/im.ts` | 5 |
| Hooks | `src/hooks/kiis/*.ts`, `src/hooks/im/*.ts` | 12 |
| Pages | `src/pages/kiis/*.tsx`, `src/pages/im/*.tsx` | 13 |
| Components | `src/components/kiis/*.tsx`, `src/components/im/*.tsx` | 5 |

---

## 9. 검증 방법

1. **개발 서버 기동**: 3개 백엔드 + 프론트엔드 동시 실행

   ```bash
   # Terminal 1: Auto FDD
   cd "Auto FDD_backup/backend" && uv run uvicorn app.main:app --port 8000
   # Terminal 2: KIIS
   cd KIIS_backup && uv run uvicorn app.main:app --port 8001
   # Terminal 3: Frontend
   cd amic-platform && npm run dev
   ```

2. **라우팅 확인**: 각 섹션(FDD/KIIS/IM) 네비게이션 정상 동작
3. **API 프록시 확인**: 브라우저 Network 탭에서 각 백엔드로 요청 분기 확인
4. **기존 기능 회귀**: FDD 기존 페이지 정상 동작 확인
5. **빌드**: `npm run build` 성공 확인
