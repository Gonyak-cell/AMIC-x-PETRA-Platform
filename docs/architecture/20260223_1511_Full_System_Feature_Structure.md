# AMIC x PETRA Platform — 전체 기능 구조 분석

> 작성일: 2026-02-23 15:11:33 | 목적: 코드 및 기능 구조 파악 (Reference Document)

---

## 1. 시스템 전체 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  amic-platform (React + Vite + TypeScript)           │
│  :5173 → nginx:3000                                 │
└──────────┬──────────┬──────────┬────────────────────┘
           │          │          │          │
        :8000      :8001      :8002      :8003
   ┌─────▼──┐ ┌─────▼──┐ ┌─────▼──┐ ┌────▼──────┐
   │  FDD   │ │  KIIS  │ │   IM   │ │ deal-mgmt │
   │ (실사) │ │(투자정보)│ │ (제안서)│ │(M&A워크플로)│
   └────┬───┘ └────┬───┘ └────┬───┘ └───────────┘
     DB:5433   DB:5434    DB:5435    DB:5436
              +Redis     +Redis
              +ES        +Celery
```

### 기술 스택

| 계층 | 기술 |
|------|------|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, GSAP (모션), Playwright (E2E) |
| **Backend** | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Database** | PostgreSQL 16 (서비스별 독립 4개), Redis 7 (2개), Elasticsearch 8.12 |
| **Async** | Celery + Redis (IM 문서 생성 비동기) |
| **Infra** | Docker Compose, Nginx 1.25 (역프록시) |
| **Auth** | JWT (공유 시크릿, SSO 구조) |
| **Doc Gen** | docxtpl + python-docx (법률 문서), PPTX 마이크로서비스 (FDD 보고서) |

---

## 2. 프론트엔드 모듈 구조 (amic-platform)

### 2.1 최상위 라우팅 (App.tsx)

```
/ (Dashboard)
├── /fdd/*       → FDD 실사 모듈
├── /kiis/*      → KIIS 투자정보 모듈
├── /docs/*      → Docs (Deal Document Studio)
├── /ma/*        → MA 인수합병 워크플로우
├── /admin/*     → 관리자
├── /settings/*  → 설정
├── /analytics/* → 분석
├── /help/*      → 도움말
├── /calendar/*  → 캘린더
└── /exports/*   → 데이터 내보내기
```

> `/im/*` → `/docs/*`로 리다이렉트 통합됨

### 2.2 FDD 모듈 (`src/modules/fdd/`)

**목적**: 재무 실사(Due Diligence) 딜 라이프사이클 관리

| 페이지 | 경로 | 기능 |
|--------|------|------|
| DealListPage | `/fdd/deals` | Deal 목록 |
| DealSetupWizardPage | `/fdd/deals/new` | 신규 Deal 생성 마법사 |
| DealWorkspacePage | `/fdd/deals/:dealId/*` | Deal 작업 공간 (멀티탭) |

**DealWorkspacePage 내부 탭** (10개):
- `MappingPage` — 계정 과목(CoA) 매핑
- `QoEPage` — Quality of Earnings (Adjusted EBITDA)
- `NWCPage` — Net Working Capital 분석
- `NetDebtPage` — 순부채 분석
- `IssuesPage` — 이슈 탐지 및 추적
- `VdrPage` — Virtual Data Room 문서 뷰어
- `ReportPage` — 실사 보고서 생성
- `DefinitionPage` — 정의 관리
- `UploadPage` — 재무 파일 업로드
- `WorkflowOverviewPage` — 워크플로우 개요

**핵심 Hooks**: `useDeals`, `useQoE`, `useNWC`, `useDebt`, `useIssues`, `useMapping`, `useVdr`, `useReportVersions`, `useUploads`

---

### 2.3 KIIS 모듈 (`src/modules/kiis/`)

**목적**: 한국 투자 정보 통합 검색 및 분석

| 페이지 | 경로 | 기능 |
|--------|------|------|
| DashboardPage | `/kiis` | KIIS 대시보드 |
| CompanyListPage | `/kiis/companies` | 기업 목록 + 필터 |
| CompanyDetailPage | `/kiis/companies/:corpCode` | 기업 상세 (재무/평판) |
| GPListPage | `/kiis/funds` | **GP 중심 펀드 검색** (운용사별 그룹화) |
| GPDetailPage | `/kiis/funds/gp/:companyCode` | GP 운용사 상세 |
| FundListPage | `/kiis/funds/all` | 펀드 전체 목록 |
| FundDetailPage | `/kiis/funds/:fundCode` | 펀드 상세 |
| ReitListPage | `/kiis/reits` | REIT 목록 |
| ReitDetailPage | `/kiis/reits/:reitsCode` | REIT 상세 |
| NewsListPage | `/kiis/news` | 금융 뉴스 목록 |
| NewsDetailPage | `/kiis/news/:articleId` | 뉴스 상세 (감정분석) |
| DealSourcingPage | `/kiis/deals` | 딜 소싱 |
| SanctionListPage | `/kiis/sanctions` | 제재 대상자 검사 |
| WatchlistPage | `/kiis/watchlist` | 관심 목록 |
| PortfolioPage | `/kiis/portfolio` | 포트폴리오 |
| ManagerListPage | `/kiis/managers` | 펀드운용사 목록 |
| ManagerProfilePage | `/kiis/managers/:managerId` | 운용사 프로필 |
| EntityResolutionPage | `/kiis/entity-resolution` | 법인 정보 통합 |
| DisclosurePage | `/kiis/disclosures` | 공시 정보 |

**핵심 Hooks**: `useGPs`, `useFunds`, `useCompanies`, `useNews`, `useAnalysis`, `useReits`, `useSanctions`, `useWatchlist`, `usePortfolio`, `useManagers`, `useDisclosures`

---

### 2.4 Docs 모듈 (`src/modules/docs/`) — Deal Document Studio

**목적**: FDD 보고서 + 법무 문서 통합 생성 스튜디오

| 페이지 | 경로 | 기능 |
|--------|------|------|
| StudioHomePage | `/docs` | 스튜디오 홈 (FDD/Legal 탭) |
| CreateDocumentPage | `/docs/new` | FDD 보고서 생성 (PPT 스타일 선택) |
| CreateLegalDocumentPage | `/docs/legal/new` | 법무 문서 생성 (SPA/SHA/NDA 등) |
| DocumentDetailPage | `/docs/documents/:id` | 문서 상세 + 다운로드 |
| TemplatesPage | `/docs/templates` | 템플릿 관리 |

**주요 컴포넌트**:
- `DocumentTypePicker` — FDD 문서 타입 선택
- `LegalDocTypePicker` — 법무 문서 타입 선택 (SPA/SHA/BTA/SSA/MOU)
- `PPTStylePicker` — PPT 테마/스타일 선택
- `LegalParamsForm` — 법무 문서 파라미터 폼
- `LegalDocumentsTab` — 법무 문서 목록 탭

**핵심 Hooks**: `useFDDDocuments`, `useLegalDocuments`, `useDocuments`, `useCompanies`

---

### 2.5 MA 모듈 (`src/modules/ma/`) — M&A 워크플로우

**목적**: 인수합병 거래의 7단계 라이프사이클 전체 추적

| 페이지 | 경로 | 기능 |
|--------|------|------|
| TransactionListPage | `/ma/transactions` | 거래 목록 + 필터 |
| CreateTransactionPage | `/ma/transactions/new` | 신규 거래 생성 |
| TransactionWorkspacePage | `/ma/transactions/:txnId/*` | 거래 상세 (멀티탭) |

**TransactionWorkspacePage 탭 구성** (15개):
1. Overview — 거래 요약 대시보드
2. Engagement — 수임계약 정보
3. Buyers — 매수자 후보 파이프라인 (13단계 상태)
4. NDAs — 기밀유지계약 추적
5. Bids — IOI/LOI/최종제안 관리
6. DD Checklist — 실사 워크스트림 (9개 카테고리: Financial/Legal/Tax/HR/IT/ESG/Regulatory/Commercial/Operational)
7. Contracts — SPA/계약 버전 관리
8. Closing — Closing 체크리스트 (15개 자동생성)
9. PMI — 인수 후 통합 태스크 (Day 1 / First 100 Days)
10. Earnout — 조건부 대금 마일스톤
11. Risks — 리스크 레지스터 (Severity 5 × Likelihood 4 매트릭스)
12. Compliance — 컴플라이언스 체크리스트 (10개 카테고리)
13. Notes — 내부 메모/커뮤니케이션
14. Approvals — 승인 워크플로우
15. Timeline — 딜 타임라인

**핵심 Hooks**: `useTransactions`, `useCompliance`, `useDDChecklist`, `useRisks`, `useClosing`, `useBids`, `useContracts`, `useNdas`, `usePMI`, `useEarnout`, `useApprovals`, `useNotes`, `useTimeline`

---

### 2.6 공통 컴포넌트 라이브러리 (~70개)

**레이아웃**: `AppShell`, `Sidebar`, `SidebarNavItem`, `PageHero`, `PageTransition` (GSAP), `ModuleSwitcher`, `HealthIndicator`

**UI 기본**: `DataTable`, `InlineSelect`, `Modal`, `Tabs`, `KpiCard`, `Badge`, `Skeleton`, `Spinner`, `Pagination`, `Select`, `Input`, `Button`, `Card`, `EmptyState`, `Breadcrumbs`

**기능 컴포넌트**:
- `CommandPalette` — 전역 검색
- `NotificationBell` + `NotificationPanel` — 알림 시스템
- `WaterfallChart`, `FinancialBarChart`, `TrendLineChart` — 금융 차트
- `GanttTimeline` — Gantt 타임라인
- `CommentThread` + `CommentInput` — 협업 댓글
- `AuthProvider` + `ProtectedRoute` — 인증 보호
- `WorkflowStepper` — 워크플로우 단계 표시
- `ActivityTimeline` — 활동 로그

**공통 Hooks** (20+): `useAuth`, `useDashboard`, `useGlobalSearch`, `useNotifications`, `useScrollReveal` (GSAP), `useTilt` (3D 틸트), `useHealthCheck`, `usePreferences`, `useProfile`

---

## 3. 백엔드 서비스 구조

### 3.1 FDD 백엔드 (`:8000`)

**목적**: 재무 실사 자동화 — 파일 수집 → 분석 → 보고서

| 엔드포인트 | 기능 |
|-----------|------|
| `GET/POST /api/v1/deals` | Deal CRUD |
| `POST /api/v1/uploads` | Excel 자동 유형 감지 업로드 |
| `GET/PUT /api/v1/mapping` | 계정 과목(CoA) 매핑 + Tie-out |
| `GET /api/v1/qoe` | Quality of Earnings (Adjusted EBITDA 계산) |
| `GET /api/v1/nwc` | Net Working Capital |
| `GET /api/v1/debt` | 부채 구조 분석 |
| `GET /api/v1/evidence` | 원문 추적 인덱싱 |
| `GET /api/v1/charts` | Waterfall/Bar/Pie/Line 차트 렌더링 |
| `GET /api/v1/issues` | 자동 이슈 탐지 (Dispute, QoE 편차) |
| `POST /api/v1/reports` | 보고서 생성 (LLM 기반 내러티브) |
| `GET /api/v1/vdr` | Virtual Data Room 연동 |
| `GET /api/v1/jobs` | 비동기 작업 오케스트레이션 |
| `GET /api/v1/templates` | 템플릿 관리 |

**특징**: RFC 7807 에러 표준, Rate Limiting (60/분), 구조화 JSON 로그

---

### 3.2 KIIS 백엔드 (`:8001`)

**목적**: 한국 투자정보 통합 — DART + KOFIA + 뉴스 수집 및 분석

| 엔드포인트 | 기능 |
|-----------|------|
| `/api/v1/dart` | 금감원 전자공시 (DART API) |
| `/api/v1/kofia` | 금융투자협회 펀드 정보 |
| `/api/v1/kofia/gp` | GP 중심 검색 (자산클래스 필터) |
| `/api/v1/kofia/funds` | 펀드 목록 (빈티지/설정액/상태 필터) |
| `/api/v1/reits` | 리츠 정보 + 분석 |
| `/api/v1/companies` | 기업 통합 조회 (법인구분 필터) |
| `/api/v1/news` | 뉴스 수집 + NLP 감정분석 |
| `/api/v1/entities` | 기업명 동일성 판별 (Entity Resolution) |
| `/api/v1/analysis/reputation` | 평판 점수 + 히스토리 |
| `/api/v1/analysis/themes` | 평판 테마 매핑 (rising/stable/risk) |
| `/api/v1/deals` | 딜 소싱 + 투자 DNA |
| `/api/v1/disclosures` | 공시 딥링크 |
| `/api/v1/portfolio` | 포트폴리오 생존분석 |
| `/api/v1/managers` | Key Man 이동 추적 |
| `/api/v1/sanctions` | 금융 제재 경중 분류 |
| `/api/v1/search` | ElasticSearch 통합검색 (기업/펀드/뉴스/딜) |
| `/api/v1/dashboard` | 시스템 대시보드 |

**특징**: Redis 캐시, Elasticsearch 8.12 전문검색, Task Scheduler (주기 데이터 갱신)

---

### 3.3 IM 백엔드 (`:8002`)

**목적**: Investment Memorandum 자동 생성 (Celery 비동기)

| 엔드포인트 | 기능 |
|-----------|------|
| `GET/POST /api/v1/documents` | IM 문서 CRUD + 다운로드 (PPT/Word) |
| `POST /api/v1/documents/{id}/upload-financials` | 재무데이터 업로드 (xlsx/csv, 10MB) |
| `GET /api/v1/companies` | 기업 정보 조회 |
| `POST /api/v1/auth` | JWT 인증 |
| `GET/POST /api/v1/users` | 사용자 관리 |
| `GET/POST /api/v1/api_keys` | API 키 관리 |

**data_source 3종**:
- `DART` — 금감원 API 자동 수집
- `MANUAL` — 수동 데이터 입력
- `EXCEL` — 재무 파일 업로드 (xlsx/xlsm/csv, 최대 10MB)

**Celery Tasks**: `generate_im` (문서 생성), `narrative` (자동 내러티브 작성), `fetch_company` (기업 정보 수집)

---

### 3.4 deal-mgmt 백엔드 (`:8003`)

**목적**: M&A 거래 관리 — 7단계 워크플로우 전체 추적

#### 3.4.1 핵심 엔티티 (22개 모델)

```
Transaction (거래 기본 정보)
├── WorkingGroup (팀원 역할)
├── Engagement (수임계약)
├── BuyerCandidate (매수자 후보, 13단계 상태)
├── NDA (기밀유지계약)
├── Bid (입찰: IOI/LOI/FINAL_OFFER)
├── DDChecklist (실사 워크스트림, 9개 카테고리)
├── Contract + ContractVersion (계약 버전 관리)
├── ClosingChecklist (15개 항목 자동생성)
├── PMITask (인수후통합, Day1/100Days)
├── Earnout (조건부대금 마일스톤)
├── Timeline (딜 이벤트)
├── Note (내부 메모)
├── Approval (승인 워크플로우)
├── RiskItem (5×4 리스크 매트릭스)
├── ComplianceItem (10개 카테고리)
├── LegalDocument (SPA/SHA/BTA/SSA/MOU 생성)
└── AuditLog (모든 변경 추적)
```

#### 3.4.2 7단계 워크플로우 (TransactionPhase)

```
ENGAGEMENT → PREPARATION → MARKETING → BIDDING_DD → NEGOTIATION → CLOSING → POST_CLOSING
```

#### 3.4.3 20개 라우터

| 라우터 | 경로 | 기능 |
|--------|------|------|
| transactions | `/api/v1/transactions` | 거래 CRUD, 필터링, 검색 |
| workflow | `/api/v1/transactions/{id}/workflow` | 7단계 상태 전환 |
| engagements | `/api/v1/engagements` | 수임계약 관리 |
| buyers | `/api/v1/buyers` | 매수자 파이프라인 |
| ndas | `/api/v1/ndas` | NDA 추적 |
| bids | `/api/v1/bids` | IOI/LOI/최종제안 |
| dd_checklists | `/api/v1/dd_checklists` | DD 워크스트림 |
| contracts | `/api/v1/contracts` | 계약 버전 관리 |
| closing | `/api/v1/closing` | Closing 체크리스트 |
| pmi | `/api/v1/pmi` | PMI 태스크 |
| earnout | `/api/v1/earnout` | 어닝아웃 마일스톤 |
| timeline | `/api/v1/timeline` | 딜 타임라인 |
| notes | `/api/v1/notes` | 내부 메모 |
| approvals | `/api/v1/approvals` | 승인 워크플로우 |
| risks | `/api/v1/risks` | 리스크 레지스터 |
| compliance | `/api/v1/compliance` | 컴플라이언스 |
| integrations | `/api/v1/integrations` | FDD/IM/KIIS 서비스 호출 |
| dashboard | `/api/v1/dashboard` | M&A KPI 대시보드 |
| legal_documents | `/api/v1/legal_documents` | 법률 문서 생성 |
| health | `/health` | 헬스체크 |

#### 3.4.4 핵심 서비스

| 서비스 파일 | 역할 |
|------------|------|
| `transaction_service.py` | CRUD, Closing 15항목 자동생성 |
| `workflow_engine.py` | 7단계 상태 전환 검증 |
| `legal_document_service.py` | docxtpl 법률 문서 렌더링 |
| `audit_service.py` | 변경 추적 로그 기록 |
| `contract_analysis_service.py` | 계약 분석 (LLM 연동 예정) |
| `fdd_client.py` | FDD API 호출 (httpx) |
| `im_client.py` | IM API 호출 (httpx) |
| `kiis_client.py` | KIIS API 호출 (httpx) |

#### 3.4.5 마이그레이션 히스토리 (8단계)

| 버전 | 내용 | 추가 테이블 수 |
|------|------|-------------|
| 001 | Phase 0~1: Transaction, Engagement, WorkingGroup, BuyerCandidate, Timeline, Audit | 6개 |
| 002 | Phase 2: NDA, Bid, DDChecklist | 3개 |
| 003 | Phase 3: Contract, ContractVersion, ClosingChecklist | 3개 |
| 004 | Phase 4: PMITask, Earnout | 2개 |
| 005 | Phase 5A: Note, Approval | 2개 |
| 006 | Phase 5B: RiskItem, ComplianceItem | 2개 |
| 007 | Phase 6: LegalDocument + 트리거 | 1개 |
| 008 | 법률 문서 인덱스 최적화 | — |

**총 테이블**: 20개

---

## 4. 인프라 구성 (Docker Compose)

### 컨테이너 목록 (15개)

| 서비스 | 포트 | 의존성 | 설명 |
|--------|------|--------|------|
| frontend | 5173 | — | Vite 개발 서버 |
| nginx | 3000 | 모든 API | 역프록시 |
| fdd-api | 8000 | fdd-db | FastAPI (FDD) |
| fdd-db | 5433 | — | PostgreSQL 16 |
| fdd-pptx | 3100 | — | Node.js PPTX 생성 마이크로서비스 |
| kiis-api | 8001 | kiis-db, kiis-redis, kiis-es | FastAPI (KIIS) |
| kiis-db | 5434 | — | PostgreSQL 16 |
| kiis-redis | 6379 | — | Redis 7 (캐시) |
| kiis-es | 9200 | — | Elasticsearch 8.12 |
| im-api | 8002 | im-db, im-redis | FastAPI (IM) |
| im-db | 5435 | — | PostgreSQL 16 |
| im-redis | 6380 | — | Redis 7 (작업 큐) |
| im-celery-worker | — | im-api, im-redis | Celery 워커 |
| im-celery-beat | — | im-redis | Celery Beat 스케줄러 |
| deal-mgmt-api | 8003 | deal-mgmt-db | FastAPI (MA) |
| deal-mgmt-db | 5436 | — | PostgreSQL 16 |

**공유 JWT 시크릿**: 모든 백엔드가 `JWT_SECRET` 동일 키 사용 (SSO 구조)

---

## 5. 서비스 간 연동 흐름

```
[사용자] → MA 거래 생성
              ↓
[deal-mgmt-api] Transaction, WorkingGroup, ClosingChecklist(15개) 저장
              ↓
[integrations.py] 마이크로서비스 호출
  • fdd_client  → FDD에 Deal 자동 생성 (fdd_deal_id 동기화)
  • im_client   → IM에 문서 자동 생성 (im_document_id 동기화)
  • kiis_client → 매수자 회사 정보 조회
              ↓
[workflow_engine] 7단계 상태 전환 검증
              ↓
[Phase 6 도달] legal_document_service
  → docxtpl 템플릿 렌더링 → SPA/SHA/BTA 문서 자동 생성
```

---

## 6. 핵심 파일 경로

### 프론트엔드
- [amic-platform/src/App.tsx](amic-platform/src/App.tsx) — 전체 라우팅 진입점
- [amic-platform/src/modules/ma/](amic-platform/src/modules/ma/) — MA 모듈 전체
- [amic-platform/src/modules/docs/](amic-platform/src/modules/docs/) — Docs 모듈 전체
- [amic-platform/src/modules/fdd/](amic-platform/src/modules/fdd/) — FDD 모듈 전체
- [amic-platform/src/modules/kiis/](amic-platform/src/modules/kiis/) — KIIS 모듈 전체
- [amic-platform/src/components/](amic-platform/src/components/) — 공통 컴포넌트 (~70개)
- [amic-platform/src/api/](amic-platform/src/api/) — API 클라이언트 (모듈별)

### 백엔드 (deal-mgmt)
- [deal-mgmt/app/main.py](deal-mgmt/app/main.py) — FastAPI 진입점 (20개 라우터 등록)
- [deal-mgmt/app/routers/](deal-mgmt/app/routers/) — 20개 라우터
- [deal-mgmt/app/models/](deal-mgmt/app/models/) — 22개 모델
- [deal-mgmt/app/services/](deal-mgmt/app/services/) — 8개 서비스
- [deal-mgmt/app/models/enums.py](deal-mgmt/app/models/enums.py) — 30개 Enum 정의
- [deal-mgmt/migrations/versions/](deal-mgmt/migrations/versions/) — 8단계 마이그레이션

### 인프라
- [docker-compose.yml](docker-compose.yml) — 개발 환경 (16개 컨테이너)
- [docker-compose.prod.yml](docker-compose.prod.yml) — 프로덕션 환경
- [nginx/dev.conf](nginx/dev.conf) — 개발 역프록시

---

## 7. 현재 개발 상태 (2026-02-23 기준)

### 완료 ✅

| 항목 | 상세 |
|------|------|
| MA 워크플로우 Phase 0~6 | 7단계 완성, 85/85 테스트 통과 |
| FDD 실사 파이프라인 | 업로드 → 분석 → 보고서 전체 |
| KIIS 투자정보 | GP 중심 검색 + 평판 테마 분석 |
| IM 자동생성 | 3가지 데이터 소스 지원 |
| Deal Document Studio | FDD + 법무 문서 통합 (Docs 모듈) |
| GSAP 모션 시스템 | 페이지 전환, ScrollReveal, 접근성 |

### 미완료 ⬜ (외부 의존)

| 항목 | 필요 조건 |
|------|---------|
| MA Phase 3: AI 계약 분석 | LLM API 키 (OpenAI/Claude) |
| MA Phase 3: DocuSign 전자서명 | DocuSign 계정 |
| 프로덕션 배포 | 서버, 도메인, SSL, GitHub Secrets |
| 사모펀드 GP 데이터 | 공공데이터포털 API 키 |

---

## 8. 모듈 규모 요약

| 모듈 | 페이지 수 | 컴포넌트 | Hook | 타입 |
|------|---------|---------|------|------|
| FDD | 15개 | Deal, Report, VDR | 9개 | 9개 |
| KIIS | 19개 | Filter, Detail, Chart | 14개 | 14개 |
| Docs | 5개 | Picker, Params, Status | 4개 | 3개 |
| MA | 3개 | (TransactionWorkspace 중심) | 12개 | 16개 |
| 공통 | — | ~70개 | 20+개 | 전역 |

| 서비스 | 라우터 | 모델 | 테이블 |
|--------|--------|------|--------|
| FDD | 20개 | 15+개 | 15+개 |
| KIIS | 17개 | 8+개 | 8+개 |
| IM | 6개 | 4개 | 4개 |
| deal-mgmt | 20개 | 22개 | 20개 |
