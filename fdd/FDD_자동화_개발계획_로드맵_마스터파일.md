# 재무회계 실사(FDD) 자동화 + 보고서(PPT/Word) 자동생성

## 전체 개발계획 로드맵 마스터파일

**Jira 백로그 수준 상세 계획**

- 작성일: 2026. 2. 5.
- 개정일: 2026. 2. 5. (v2 통합)
- 기준: Completion Accounts 및 Locked Box 모두 지원

---

## 목차

1. [프로젝트 개요 및 전제](#1-프로젝트-개요-및-전제)
2. [Jira 프로젝트 구조 및 규칙](#2-jira-프로젝트-구조-및-규칙)
3. [아키텍처 결정 & 기술 스택](#3-아키텍처-결정--기술-스택) ← NEW
4. [개발 규칙 (Rules)](#4-개발-규칙-rules) ← NEW
5. [API 설계 명세](#5-api-설계-명세) ← NEW
6. [AI 에이전트 설계 (Agent)](#6-ai-에이전트-설계-agent) ← NEW
7. [CI/CD 및 DevOps](#7-cicd-및-devops) ← NEW
8. [회계 도메인 특화 규칙](#8-회계-도메인-특화-규칙) ← NEW
9. [EPIC 상세 내용 (18개 EPIC)](#9-epic-상세-내용)
10. [우선순위 및 최소 경로 (MVP)](#10-우선순위-및-최소-경로-mvp)
11. [개발 착수 전 최종 체크리스트](#11-개발-착수-전-최종-체크리스트) ← NEW
12. [참고 문헌 및 전거](#12-참고-문헌-및-전거)

---

## 1. 프로젝트 개요 및 전제

### 1.1 프로젝트 목적

본 프로젝트는 재무회계 실사(Financial Due Diligence, FDD) 업무의 자동화와 PPT/Word 보고서 자동생성을 목표로 합니다. Completion Accounts 및 Locked Box 방식 모두를 지원하며, 거래별 정의(Definitions)와 근거(Evidence) 추적을 핵심 기능으로 포함합니다.

### 1.2 핵심 전제 (리서치 기반)

- **Working Capital, Net Debt, debt-like/cash-like**는 법률 또는 IFRS상 고정 정의가 아니며, 거래별로 정의가 필요하고 분쟁 지점이 되기 쉬움
- **기술(대량 전자정보/분석도구)** 사용 시에도 "신뢰성 있는 증거 확보 및 문서화" 책임을 명확히 해야 하며, 보고서 자동생성에서도 근거(라인리지) 강제가 필요
- **PPTX/DOCX 자동생성**은 OOXML 기반(표준화된 ZIP+XML 패키지)이므로, "중간표현(Report Schema) → 렌더러(Renderer)" 구조로 설계해야 템플릿/출력 포맷 확장이 가능

---

## 2. Jira 프로젝트 구조 및 규칙

### 2.1 프로젝트 키 및 이슈 유형

| 항목 | 내용 |
|------|------|
| 프로젝트 키 | FDD |
| 이슈 유형 | Epic / Story / Task / Bug / Test |
| 라벨(권장) | report, pptx, docx, evidence, definition, qoe, nwc, netdebt, security, regression |

### 2.2 공통 DoD(Definition of Done) 필수 항목

**모든 Story에 적용되는 완료 기준:**

1. 수용기준(AC) 전부 충족 (정량/정성 모두)
2. 단위 테스트(필수), 회귀 테스트(해당 시) 통과
3. 로그/감사추적 (누가/언제/무엇을 변경) 기록
4. "근거 링크(EvidenceLink)"가 요구되는 산출물은 링크 누락 0건
5. 동일 입력/동일 정의/동일 버전에서 결과 재현 (해시/스냅샷 기반)

---

## 3. 아키텍처 결정 & 기술 스택

### 3.1 아키텍처 선택: 옵션 3 — Python Backend + React Frontend

#### 3.1.1 채택 근거

본 프로젝트는 아키텍처 검토 시 3가지 옵션을 비교하였으며, **옵션 3 "Python Backend + React Frontend"**를 채택하였습니다.

| 옵션 | 구성 | 채택 여부 | 사유 |
|------|------|-----------|------|
| 옵션 1 | Full Python (Django/Flask) | ❌ 제외 | FE 표현력 부족, 복잡 UI(스프레드시트/드래그&드롭) 구현 한계 |
| 옵션 2 | Full JavaScript (Node.js + React) | ❌ 제외 | 회계 계산(Decimal), ML(pandas/scikit-learn), 문서 처리(python-docx) 생태계 부족 |
| **옵션 3** | **Python BE + React FE** | **✅ 채택** | 회계 계산/ML에 최적인 Python + 복잡 UI에 강한 React 조합 |
| 옵션 4 | Desktop App (Electron 등) | ❌ 제외 | 협업/배포/업데이트 어려움, 웹 기반 우위 |

#### 3.1.2 핵심 설계 원칙

- **Report Schema IR 패턴**: engines → report_builder.py → JSON IR → renderers (PPT/Word)
- **EvidenceLink**: 다형 연관(polymorphic association) — target_type/target_id → source_type/source_id/source_detail
- **Engine 함수**: 순수 함수, `tuple[Result, list[EvidenceLink]]` 반환, DB 접근 금지
- **Snapshot hashing**: definition_hash + input_hash + engine_version → result_hash (재현성 보장)

### 3.2 기술 스택 확정

> **충돌 해결 방침**: v2 검토안과 현재 구현이 상이한 경우, 이미 구현된 Sprint 1 결정을 우선하고 향후 전환 필요 시 별도 Sprint에서 처리합니다.

| 영역 | 기술 | 버전 | 용도 | 비고 |
|------|------|------|------|------|
| Language (BE) | **Python** | **3.12** | 백엔드, 계산 엔진, ML | v2는 3.11+ → 3.12로 확정 |
| Framework (BE) | **FastAPI** | 0.100+ | REST API, 비동기 처리 | |
| ORM | **SQLAlchemy** | 2.x | DB 접근, mapped_column 스타일 | |
| Migration | **Alembic** | - | DB 마이그레이션 | |
| Language (FE) | **TypeScript** | 5.0+ | 프론트엔드 개발 | |
| Framework (FE) | **React + Vite** | React 19 | SPA, 빌드 | v2는 Next.js 14+ → React+Vite 확정 |
| 상태관리 (FE) | **TanStack Query** | - | 서버 상태 관리 | v2는 Zustand+RQ → TanStack Query 확정 |
| 스타일링 (FE) | **Tailwind CSS** | - | 유틸리티 CSS | |
| 차트 (FE) | Recharts | - | NWC 트렌드, QoE 브리지 | |
| 테이블 (FE) | TanStack Table | - | 스케줄/스프레드시트 UI | |
| PPT 생성 | **PptxGenJS** | - | Node.js sidecar (port 3100) | v2의 Open XML SDK 제외, sidecar 확정 |
| Word 생성 | **python-docx / docxtpl** | - | DOCX 보고서 | |
| Excel 처리 | **openpyxl + pandas** | - | Excel 읽기/쓰기/분석 | |
| ML | **pandas + scikit-learn** | - | 이상치 탐지, 데이터 분석 | |
| AI/LLM | Claude / GPT-4o | - | 문서 분석, 판단 지원 | |
| DB | **PostgreSQL** | 16+ | 메인 DB (UUID PK, JSONB) | |
| Infra | **Docker Compose** | - | 개발/배포 환경 | |
| **향후 검토** | Celery + Redis | - | Task Queue (비동기 작업) | 현재 불필요, 향후 Sprint에서 도입 |
| **향후 검토** | Elasticsearch | 8+ | 전표 검색, 전문 검색 | |
| **향후 검토** | Auth0 / Keycloak | - | SSO, MFA | |
| **향후 검토** | Sentry | - | 에러 모니터링 | |

#### 충돌 해결 상세

| 항목 | v2 제안 | 적용 결정 | 사유 |
|------|---------|-----------|------|
| Frontend | Next.js 14+ | React 19 + Vite | Sprint 1 완료, 이미지에서도 React 추천 |
| 상태관리 | Zustand + React Query | TanStack Query | 이미 구현됨, 필요시 Zustand 추가 |
| Python | 3.11+ | 3.12 | 이미 3.12 사용 중 |
| 폴더 구조 | api/v1/ 하위 모듈 분리 | 현재 flat + 향후 전환 노트 | Sprint 1 구조 유지, 점진적 확장 |
| PPT | PptxGenJS + Open XML SDK | PptxGenJS sidecar | 이미 pptx-service 구축됨 |
| Task Queue | Celery + Redis | 향후 Sprint에서 도입 | 현재 불필요 |
| Desktop App | 옵션으로 언급 | 제외 | 이미지에서 명시적 제외 |

### 3.3 프로젝트 폴더 구조

#### 3.3.1 현재 구조 (Sprint 1 완료 시점)

```
auto-fdd/
├── backend/                          # Python FastAPI 백엔드
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 앱 엔트리
│   │   ├── config.py                 # 환경 설정
│   │   ├── database.py               # DB 연결/세션
│   │   ├── api/                      # API 라우터 (현재 flat 구조)
│   │   │   ├── __init__.py
│   │   │   └── deals.py              # 딜 관리 API
│   │   ├── models/                   # SQLAlchemy 모델
│   │   │   ├── __init__.py
│   │   │   ├── deal.py               # Deal, DealDefinition, Snapshot
│   │   │   └── audit.py              # AuditLog
│   │   ├── schemas/                  # Pydantic 스키마
│   │   │   ├── __init__.py
│   │   │   └── deal.py               # DealCreate, DealRead 등
│   │   ├── services/                 # 비즈니스 로직
│   │   │   ├── __init__.py
│   │   │   └── snapshot_service.py   # 스냅샷 생성/해시
│   │   ├── engines/                  # 계산 엔진 (향후 구현)
│   │   ├── renderers/                # 보고서 렌더러 (향후 구현)
│   │   ├── qa/                       # 품질 검사 (향후 구현)
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── hashing.py            # 해시 유틸리티
│   ├── alembic/                      # DB 마이그레이션
│   │   └── env.py
│   └── tests/                        # 테스트
│       ├── __init__.py
│       ├── conftest.py               # SQLite 인메모리 fixture
│       ├── test_deals.py
│       └── test_hashing.py
├── frontend/                         # React + Vite 프론트엔드
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                    # 라우팅
│       ├── api/
│       │   └── client.ts             # Axios 클라이언트
│       ├── types/
│       │   └── deal.ts               # TypeScript 타입
│       ├── hooks/
│       │   └── useDeals.ts           # TanStack Query 훅
│       ├── components/
│       │   └── layout/
│       │       └── AppShell.tsx       # 레이아웃 쉘
│       └── pages/
│           ├── DealListPage.tsx
│           ├── DealWorkspacePage.tsx
│           └── DefinitionPage.tsx
├── pptx-service/                     # Node.js PPT 생성 사이드카
│   ├── src/
│   │   └── index.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
└── docker-compose.yml
```

#### 3.3.2 향후 확장 구조 (Sprint 2~8+)

```
auto-fdd/
├── backend/
│   ├── app/
│   │   ├── api/                      # Sprint 확장 시 모듈별 분리
│   │   │   ├── deals.py
│   │   │   ├── ingestion.py          # Sprint 2: 데이터 업로드
│   │   │   ├── mapping.py            # Sprint 3: 계정매핑
│   │   │   ├── qoe.py                # Sprint 4: QoE 분석
│   │   │   ├── nwc.py                # Sprint 5: NWC 분석
│   │   │   ├── debt.py               # Sprint 5: Net Debt 분석
│   │   │   └── reports.py            # Sprint 7: 리포트 생성
│   │   ├── models/
│   │   │   ├── deal.py
│   │   │   ├── audit.py
│   │   │   ├── evidence.py           # Sprint 3: EvidenceLink
│   │   │   ├── account.py            # Sprint 3: 계정/매핑
│   │   │   ├── journal_entry.py      # Sprint 2: 전표
│   │   │   ├── qoe_bridge.py         # Sprint 4: QoE 브리지
│   │   │   ├── nwc_schedule.py       # Sprint 5: NWC 스케줄
│   │   │   └── debt_schedule.py      # Sprint 5: Debt 스케줄
│   │   ├── services/
│   │   │   ├── snapshot_service.py
│   │   │   ├── ingestion/            # Sprint 2: 데이터 인제스트
│   │   │   │   ├── parser.py
│   │   │   │   ├── validator.py
│   │   │   │   └── coa_mapper.py
│   │   │   └── evidence/             # Sprint 3: Evidence Ledger
│   │   │       ├── ledger.py
│   │   │       └── tracer.py
│   │   ├── engines/                  # 순수 계산 엔진
│   │   │   ├── qoe_engine.py         # Sprint 4
│   │   │   ├── nwc_engine.py         # Sprint 5
│   │   │   ├── debt_engine.py        # Sprint 5
│   │   │   └── anomaly_detector.py   # Sprint 6
│   │   ├── renderers/                # 보고서 렌더러
│   │   │   └── report_builder.py     # Sprint 7: IR → JSON
│   │   ├── qa/                       # 품질 게이트
│   │   │   └── report_qa.py          # Sprint 8
│   │   ├── rules/                    # 비즈니스 룰 정의
│   │   │   ├── addback_rules.py
│   │   │   ├── debtlike_rules.py
│   │   │   └── anomaly_rules.py
│   │   ├── agents/                   # AI 에이전트 (향후)
│   │   │   ├── orchestrator.py
│   │   │   ├── contract_analyzer.py
│   │   │   └── adjustment_advisor.py
│   │   └── tasks/                    # 비동기 작업 (Celery 도입 시)
│   │       ├── ingestion_tasks.py
│   │       ├── analysis_tasks.py
│   │       └── report_tasks.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── layout/
│       │   ├── deal/
│       │   ├── qoe/
│       │   ├── nwc/
│       │   ├── debt/
│       │   └── common/
│       ├── hooks/
│       ├── types/
│       └── pages/
├── pptx-service/
├── infrastructure/                   # IaC (향후)
│   ├── docker/
│   ├── k8s/
│   └── terraform/
├── docs/                             # 문서 (향후)
│   ├── api/
│   ├── architecture/
│   └── rules/
└── .github/
    └── workflows/                    # CI/CD (향후)
        ├── ci.yml
        └── deploy.yml
```

---

## 4. 개발 규칙 (Rules)

### 4.1 코딩 표준 (Coding Standards)

#### 4.1.1 Python Backend 규칙

- Python 버전: **3.12** (타입 힌트 필수 사용)
- 코드 포매터: **Black** (라인 길이 88자)
- 린터: **Ruff** (flake8 + isort + pyflakes 통합)
- 타입 검사: **mypy** (strict 모드)
- 독스트링: **Google 스타일**
- import 순서: stdlib → third-party → local (isort 자동 정렬)

**네이밍 규칙:**

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | snake_case | `qoe_engine.py`, `nwc_calculator.py` |
| 클래스 | PascalCase | `QoEBridge`, `NWCSchedule`, `DebtClassifier` |
| 함수/메서드 | snake_case | `calculate_ebitda()`, `detect_anomaly()` |
| 상수 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_CURRENCY` |
| 변수 | snake_case | `trial_balance`, `journal_entries` |
| Private | _접두사 | `_validate_input()`, `_parse_gl()` |
| 환경변수 | UPPER_SNAKE_CASE | `DATABASE_URL`, `SECRET_KEY` |
| API 엔드포인트 | kebab-case | `/api/v1/qoe-bridge`, `/api/v1/nwc-schedule` |

**함수 규칙:**

- 함수 하나에 한 가지 책임 (Single Responsibility)
- 함수 길이 50줄 이내 권장 (초과 시 분리)
- 인자 5개 이내 (초과 시 데이터 클래스/dict 사용)
- 반환 타입 항상 명시: `def calc_ebitda(tb: TrialBalance) -> Decimal:`
- 비즈니스 로직에 예외 처리 필수 (try-except는 구체적 예외만 잡기)

#### 4.1.2 React Frontend 규칙

- **TypeScript 필수** (any 사용 금지)
- 함수형 컴포넌트 + Hooks만 사용 (class 컴포넌트 금지)
- 상태관리: **TanStack Query** (서버 상태), 필요시 Zustand 추가
- 스타일링: **Tailwind CSS**
- 컴포넌트 네이밍: PascalCase (`QoEBridgeTable.tsx`)
- 페이지 네이밍: PascalCase (`DealListPage.tsx`)
- 커스텀 훅: use 접두사 (`useQoEData`, `useNWCSimulation`)

#### 4.1.3 데이터베이스 규칙

- 테이블명: snake_case, 복수형 (`journal_entries`, `qoe_bridges`)
- 컬럼명: snake_case (`created_at`, `account_id`)
- PK: **UUID v4** (auto-increment 사용 금지 — 보안 및 분산 대응)
- FK: `{참조테이블_단수}_id` (`company_id`, `account_id`)
- 인덱스: `idx_{테이블}_{컬럼}` (`idx_journal_entries_entry_date`)
- **Soft delete**: `deleted_at` 컬럼 (실제 삭제 금지 — 감사추적)
- 모든 테이블에 `created_at`, `updated_at` 필수
- **금액: DECIMAL(18,4) 타입** (FLOAT 절대 금지)
- 마이그레이션: **Alembic** (수동 SQL 금지)
- JSONB: 유연한 스키마 필드 (definition_data, audit old/new values)

---

### 4.2 Git 워크플로우 규칙

#### 4.2.1 브랜치 전략 (Git Flow 간소화)

| 브랜치 | 용도 | 규칙 |
|--------|------|------|
| `main` | 프로덕션 배포 | 직접 커밋 금지, PR만 허용 |
| `develop` | 개발 통합 | feature에서 PR 머지 |
| `feature/{이슈번호}-{설명}` | 기능 개발 | develop에서 분기, 1기능=1브랜치 |
| `bugfix/{이슈번호}-{설명}` | 버그 수정 | develop에서 분기 |
| `hotfix/{이슈번호}-{설명}` | 긴급 수정 | main에서 분기 → main + develop 머지 |
| `release/{버전}` | 릴리즈 준비 | develop에서 분기 → main 머지 |

#### 4.2.2 커밋 메시지 규칙 (Conventional Commits)

**형식:** `{type}({scope}): {description}`

| Type | 용도 | 예시 |
|------|------|------|
| `feat` | 새 기능 | `feat(qoe): add EBITDA bridge generator` |
| `fix` | 버그 수정 | `fix(parser): handle empty GL rows` |
| `refactor` | 리팩토링 | `refactor(nwc): extract peg calculator` |
| `test` | 테스트 추가 | `test(debt): add debt-like classification tests` |
| `docs` | 문서 수정 | `docs(api): update QoE endpoint spec` |
| `chore` | 설정/빌드 | `chore(ci): add GitHub Actions pipeline` |

#### 4.2.3 코드 리뷰 규칙

- PR 머지 조건: **리뷰어 1명 이상 승인 + CI 통과**
- PR 크기: **최대 400줄** (초과 시 분리 요청)
- 셀프 머지 금지
- PR 설명 필수: 무엇을/왜/어떻게 + 스크린샷(UI 변경 시)

---

### 4.3 테스트 규칙

#### 4.3.1 테스트 종류 및 커버리지 목표

| 테스트 종류 | 도구 | 커버리지 목표 | 필수 대상 |
|-------------|------|---------------|-----------|
| Unit Test | pytest | 80% 이상 | 계산 엔진 (QoE/NWC/Net Debt) |
| Integration Test | pytest + testcontainers | 핵심 플로우 | 데이터 파이프라인, API |
| E2E Test | Playwright | 핵심 시나리오 | 업로드→분석→리포트 플로우 |
| 금액 정확성 Test | pytest (특수) | **100%** | EBITDA 계산, NWC peg, Net debt |

> **현재**: conftest.py에서 SQLite in-memory 사용. PostgreSQL-specific 기능(JSONB 등) 테스트는 별도 조정 필요.

#### 4.3.2 회계 계산 테스트 특별 규칙

> ⚠️ **회계 프로그램 특성상 숫자 정확성은 생명입니다.**

- **모든 금액 계산 함수는 반드시 테스트 동반** (TDD 권장)
- **Decimal 사용 필수** (float 연산 금지 — 부동소수점 오차 방지)
- tie-out 검증: 차변합계 = 대변합계, TB합계 = FS합계 자동 체크
- 경계값 테스트: 0원, 음수, 매우 큰 금액, 소수점 4자리
- 통화 변환 테스트: 원화/달러/엔화 혼합 시나리오
- 라운딩 규칙: 원단위 절사/반올림 일관성 검증
- 과거 딜 데이터(익명화)로 회귀 테스트 구축

---

### 4.4 에러 처리 규칙

#### 4.4.1 에러 코드 체계

| 코드 범위 | 영역 | 예시 |
|-----------|------|------|
| 1000-1999 | 데이터 인제스트 에러 | 1001: TB 합계 불일치, 1002: GL 기간 누락 |
| 2000-2999 | 계정 매핑 에러 | 2001: 미매핑 계정 존재, 2002: 매핑 충돌 |
| 3000-3999 | QoE 계산 에러 | 3001: EBITDA 음수, 3002: 조정항목 근거 미비 |
| 4000-4999 | NWC 계산 에러 | 4001: NWC 정의 미설정, 4002: 기간 데이터 부족 |
| 5000-5999 | Net Debt 계산 에러 | 5001: Debt 분류 미완료, 5002: 리스 데이터 부족 |
| 6000-6999 | 문서 처리 에러 | 6001: OCR 실패, 6002: 계약서 파싱 오류 |
| 9000-9999 | 시스템 에러 | 9001: DB 연결 실패, 9002: 파일 처리 오류 |

#### 4.4.2 에러 심각도

- **CRITICAL**: 데이터 무결성 위협 (tie-out 불일치, 금액 오차) → 즉시 중단 + 알림
- **ERROR**: 기능 실행 불가 (파서 실패, 계산 불가) → 재시도 후 사용자 알림
- **WARNING**: 결과 신뢰도 하락 (매핑 낮은 신뢰도, 데이터 누락) → 계속 + 경고
- **INFO**: 정상 처리 정보 (처리 완료, 후보 생성) → 로그만

---

### 4.5 로깅 규칙

- **구조화 로그 (JSON 형식)** 사용 — ELK/Grafana 연동 대비
- 로그에 전표번호/파일명/사용자 등 컨텍스트 필수 포함
- **개인정보 절대 로그에 포함 금지** (주민등록번호, 급여 금액 등)
- 금액 로그는 마스킹 처리 (`123,456,789` → `1**,***,**9`)
- 감사 로그는 별도 테이블/스토리지에 **90일 이상 보관**

---

## 5. API 설계 명세

### 5.1 API 설계 원칙

- **REST API** (JSON 기반)
- 버전관리: URL 경로 방식 (`/api/v1/`)
- 인증: **JWT Bearer Token** (OAuth 2.0)
- 페이지네이션: **cursor 기반** (offset 미사용)
- 에러 응답: **RFC 7807** (Problem Details) 형식
- Rate Limiting: 사용자당 100 req/min

### 5.2 핵심 API 엔드포인트

| Method | Endpoint | 설명 | Sprint |
|--------|----------|------|--------|
| `POST` | `/api/v1/deals` | 딜(프로젝트) 생성 | 1 ✅ |
| `GET` | `/api/v1/deals` | 딜 목록 조회 | 1 ✅ |
| `GET` | `/api/v1/deals/{id}` | 딜 상세 조회 | 1 ✅ |
| `PUT` | `/api/v1/deals/{id}/definition` | Deal Definition 설정 | 1 ✅ |
| `POST` | `/api/v1/deals/{id}/snapshots` | 스냅샷 생성 | 1 ✅ |
| `POST` | `/api/v1/deals/{id}/upload` | 데이터 파일 업로드 | 2 ✅ |
| `POST` | `/api/v1/deals/{id}/ingest` | 데이터 인제스트 실행 | 2 ✅ |
| `GET` | `/api/v1/deals/{id}/validation` | 데이터 검증 결과 조회 | 2 ✅ |
| `GET/PUT` | `/api/v1/deals/{id}/coa-mapping` | 계정 매핑 조회/수정 | 3 ✅ |
| `POST` | `/api/v1/deals/{id}/qoe/analyze` | QoE 분석 실행 | 4 ✅ |
| `GET` | `/api/v1/deals/{id}/qoe/bridge` | QoE 브리지 조회 | 4 ✅ |
| `PUT` | `/api/v1/deals/{id}/qoe/adjustments/{adj_id}` | 조정항목 상태 변경 | 4 ✅ |
| `POST` | `/api/v1/deals/{id}/nwc/analyze` | NWC 분석 실행 | 5 ✅ |
| `GET` | `/api/v1/deals/{id}/nwc/schedule` | NWC 스케줄 조회 | 5 ✅ |
| `POST` | `/api/v1/deals/{id}/nwc/simulate` | NWC peg 시뮬레이션 | 5 ✅ |
| `POST` | `/api/v1/deals/{id}/debt/analyze` | Net Debt 분석 실행 | 5 ✅ |
| `GET` | `/api/v1/deals/{id}/debt/schedule` | Debt 스케줄 조회 | 5 ✅ |
| `GET` | `/api/v1/deals/{id}/issues` | 이슈 로그 조회 | 6 |
| `POST` | `/api/v1/deals/{id}/reports/generate` | 리포트 생성 | 7 |
| `GET` | `/api/v1/deals/{id}/evidence/{item_id}` | 근거 추적 조회 | 3 ✅ |

---

## 6. AI 에이전트 설계 (Agent)

> 기존 마스터파일에서 **가장 크게 누락된 부분**입니다. FDD 자동화에서 AI/LLM은 핵심 차별점이 됩니다.

### 6.1 에이전트 아키텍처 개요

시스템은 **멀티 에이전트 구조**로 설계합니다. 각 에이전트는 특정 역할을 수행하며, 오케스트레이터가 전체 흐름을 조율합니다.

#### 6.1.1 에이전트 구성 (9개)

| 에이전트 | 역할 | LLM 사용 | 입력 | 출력 |
|----------|------|----------|------|------|
| **Orchestrator** | 전체 분석 흐름 조율 | Yes | 사용자 요청 | 작업 분배/상태 관리 |
| **Data Parser Agent** | 데이터 구조 인식/변환 | Partial | Excel/CSV 파일 | 정형화된 데이터 |
| **CoA Mapper Agent** | 계정 매핑 제안 | Yes | 원천 계정명 + 패턴 | 매핑 제안 + 신뢰도 |
| **QoE Analyzer Agent** | 조정항목 탐지/제안 | Yes | GL + 탐지 결과 | 조정 후보 + 근거 |
| **NWC Classifier Agent** | 구성항목 분류 지원 | Yes | 계정 목록 + 잔액 | Operating/Cash/Debt 분류 |
| **Debt Classifier Agent** | Debt-like 분류 지원 | Yes | 항목 목록 + 계약 정보 | 분류 근거 생성 |
| **Contract Analyzer Agent** | 계약서 조항 추출 | Yes | 계약서 텍스트 | 구조화된 조항 데이터 |
| **Report Writer Agent** | 보고서 초안 작성 | Yes | 분석 결과 전체 | 보고서 초안 |
| **Evidence Tracer Agent** | 근거 링크 관리 | No | 계산 결과 + 원천 | Evidence Ledger 갱신 |

#### 6.1.2 에이전트 상호작용 흐름

1. 사용자 → **Orchestrator**: 분석 요청
2. Orchestrator → **Data Parser Agent**: 데이터 파싱 지시
3. Data Parser Agent → **CoA Mapper Agent**: 매핑 요청 (파싱 완료 후)
4. CoA Mapper Agent → **[사용자 승인 대기]**: 매핑 결과 제시
5. 승인 후 → **QoE Analyzer Agent**: QoE 분석 시작
6. **병렬**: NWC Classifier Agent + Debt Classifier Agent 동시 실행
7. **Evidence Tracer Agent**: 전 과정에서 근거 자동 기록
8. 전체 완료 → **Report Writer Agent**: 보고서 초안 생성
9. Orchestrator → 사용자: 결과 전달 + 리뷰 요청

### 6.2 에이전트별 상세 설계

#### 6.2.1 QoE Analyzer Agent (핵심)

**역할:** GL/전표 데이터에서 EBITDA 조정항목 후보를 탐지하고, 각 후보에 대해 분류와 근거를 제시

**처리 흐름:**

1. 룰 엔진이 1차 후보 생성 (키워드, 금액 이상치, 계정 패턴)
2. LLM이 후보별 맥락 분석 (적요 해석, 경상/비경상 판단 지원)
3. 결과를 신뢰도와 함께 사용자에게 제시
4. 사용자가 채택/기각 → 학습 데이터 축적

**프롬프트 설계 원칙:**

- 시스템 프롬프트에 "FDD 전문 회계사" 역할 부여
- Deal Definition(EBITDA 정의, Add-back 정책)을 컨텍스트로 제공
- 전표 데이터는 구조화된 JSON으로 전달 (토큰 절약)
- 출력은 반드시 **JSON 스키마 강제** (Structured Output)
- 판단 근거를 반드시 포함하도록 지시

**출력 JSON 스키마:**

```json
{
  "adjustment_candidates": [
    {
      "journal_entry_id": "GL-12345",
      "description": "외부 법률자문 비용",
      "amount": 150000000,
      "category": "one-off",
      "direction": "add-back",
      "rationale": "M&A 거래 관련 일회성 법률자문으로 경상적 비용 아님",
      "confidence": 0.85,
      "additional_info_needed": null
    }
  ]
}
```

#### 6.2.2 Contract Analyzer Agent

**역할:** 계약서(매출/리스/차입)에서 회계적으로 중요한 조항을 추출

- 입력: 계약서 텍스트 (OCR 또는 PDF 추출)
- 지시: IFRS 15 5-step 모델 각 단계별 관련 조항 식별
- 출력: 구조화된 JSON (수행의무, 변동대가, 인도시점 등)
- 플래그: 매출인식 시점 리스크, 변동대가 존재 여부 등

#### 6.2.3 Report Writer Agent

**역할:** 분석 결과를 종합하여 FDD 보고서 초안 작성

- 입력: QoE/NWC/Net Debt 분석 결과 + 이슈 로그
- 출력: Report Schema IR (JSON) → 렌더러(PPT/Word)로 전달
- **핵심: 결론이 아닌 '발견사항' 톤으로 작성** (감사/증명 경계)
- 모든 숫자에 Evidence Ledger 참조 포함

### 6.3 LLM 사용 규칙

#### 6.3.1 LLM 호출 원칙

- **결정론적 계산(EBITDA, NWC, Net Debt)에는 LLM 사용 금지** → 룰 엔진만
- LLM은 **"판단 지원/제안/텍스트 분석"**에만 사용
- 모든 LLM 출력은 **Structured Output (JSON Schema) 강제**
- LLM 출력은 "후보/제안"일 뿐, **자동 확정 금지**
- 사용자 승인 없이 LLM 결과가 최종 산출물에 반영되면 안 됨

#### 6.3.2 프롬프트 관리 규칙

- 프롬프트 **버전 관리 필수** (`prompt_v1.0.yaml` 형태)
- 프롬프트 변경 시 **A/B 테스트** 수행
- 프롬프트에 Deal Definition을 **동적 주입**
- Few-shot 예시는 과거 딜(익명화)에서 추출
- **토큰 사용량/비용 모니터링** 필수
- 할루시네이션 방지: 숫자는 항상 원천 데이터와 **교차 검증**

#### 6.3.3 LLM 모델 선택 전략

| 용도 | 권장 모델 | 이유 |
|------|-----------|------|
| 계약서 분석 (긴 문서) | Claude Sonnet | 200K 토큰 컨텍스트, 문서 이해력 |
| 전표 분류/제안 | GPT-4o-mini | 빠른 응답, 비용 효율 |
| 보고서 초안 | Claude Sonnet | 긴 출력, 한국어 품질 |
| CoA 매핑 제안 | GPT-4o-mini | 간단한 분류, 비용 효율 |
| Fallback | Claude Opus / GPT-4o | 복잡한 판단, 높은 정확도 필요시 |

### 6.4 에이전트 안전장치 (Guardrails)

> ⚠️ **회계 소프트웨어에서 AI 오류는 곧 금전적 손실입니다.**

**필수 Guardrails:**

- **금액 교차검증**: LLM이 언급한 금액은 반드시 원천 데이터와 대조
- **합계 검증**: LLM 산출 항목 합계 ≠ 룰 엔진 합계 시 경고
- **할루시네이션 탐지**: 존재하지 않는 전표ID/계정 참조 시 차단
- **신뢰도 하한**: LLM confidence < 0.3이면 결과 비노출
- **토큰 제한**: 1회 호출 최대 토큰 제한 (비용 폭주 방지)
- **Rate Limit**: 딜 당 LLM 호출 횟수 상한 설정
- **인간 승인 게이트**: 모든 LLM 결과는 사용자 확인 후 반영

---

## 7. CI/CD 및 DevOps

### 7.1 환경 분리

| 환경 | 용도 | 데이터 | 접근 |
|------|------|--------|------|
| Local | 개발자 로컬 | 더미/시드 데이터 | 개발자만 |
| Dev | 개발 통합 | 익명화 샘플 데이터 | 개발팀 |
| Staging | QA/테스트 | 프로덕션 미러(마스킹) | 개발팀 + QA |
| Production | 운영 | 실제 데이터 | 운영팀 (MFA 필수) |

### 7.2 CI/CD 파이프라인

#### 7.2.1 PR 시 자동 실행

1. 코드 포매팅 검사 (Black + Ruff)
2. 타입 검사 (mypy)
3. Unit Test 실행 (pytest)
4. 커버리지 체크 (80% 미달 시 실패)
5. 보안 스캔 (Bandit — Python 취약점)
6. 의존성 취약점 스캔 (pip-audit)

#### 7.2.2 develop 머지 시

1. Integration Test 실행
2. Docker 이미지 빌드
3. Dev 환경 자동 배포

#### 7.2.3 main 머지 시 (릴리즈)

1. 전체 테스트 스위트
2. Docker 이미지 태깅 (시맨틱 버전)
3. Staging 배포 → 수동 승인 → Production 배포
4. 릴리즈 노트 자동 생성

### 7.3 모니터링 전략

| 대상 | 도구 | 알림 조건 |
|------|------|-----------|
| 서버 상태 | Prometheus + Grafana | CPU/메모리 80% 초과 |
| API 응답시간 | Prometheus + Grafana | P95 > 5초 |
| 에러율 | Sentry | 에러율 1% 초과 |
| DB 성능 | pg_stat_statements | 쿼리 실행시간 > 3초 |
| LLM 비용 | 커스텀 대시보드 | 일일 비용 임계치 초과 |
| 보안 이벤트 | CloudWatch / ELK | 비정상 접근 패턴 |

---

## 8. 회계 도메인 특화 규칙

### 8.1 금액 처리 규칙

> ⚠️ **이 규칙은 절대 위반해서는 안 됩니다.**

- **모든 금액은 Decimal 타입 사용** (float 금지)
- 원화 기준 소수점 없음 (정수 처리)
- 외화 금액은 소수점 4자리까지
- 환율 적용: 발생일 환율(거래) / 기말 환율(잔액)
- 라운딩: 원단위 반올림 (거래별), 백만원 반올림 (보고서)
- **차변/대변 합계 일치 검증은 모든 처리 후 자동 실행**

### 8.2 기간 처리 규칙

- 회계기간: 시작일~종료일 (inclusive)
- 월마감: 매월 말일 기준 (윤년/월말 자동 처리)
- 비교 기간: 직전 기간, 전년 동기 자동 생성
- LTM/TTM: 최근 12개월 자동 계산
- YTD: 회계연도 시작일부터 기준일까지

### 8.3 Deal Definition 변경 규칙

- Definition 변경 시 **모든 관련 분석 결과 자동 무효화**
- 무효화된 결과에 대해 재실행 필요 표시
- 변경 전/후 비교 자동 생성
- 변경 이력은 **삭제 불가** (감사추적)

### 8.4 데이터 무결성 규칙

- 업로드된 원본 파일은 **절대 수정 금지** (읽기 전용)
- 모든 처리는 원본의 사본에서 수행
- 처리 완료 후 결과 해시 저장 (변조 탐지)
- 동시 접근 시 **낙관적 잠금** (Optimistic Locking) 적용
- Evidence Ledger는 **append-only** (수정/삭제 불가)

### 8.5 사용자 경험(UX) 규칙

- 분석 진행 상태를 **실시간 표시** (Progress bar + 단계명)
- 에러 발생 시 기술 용어 대신 **회계 용어로 안내**
- 조정항목 채택/기각 시 **한 번 더 확인** (실수 방지)
- 모든 숫자를 클릭하면 원천 데이터로 이동 (**Drill-down**)
- Excel 다운로드는 모든 스케줄에서 항상 가능
- 작업 중간 저장 자동 (5분마다 또는 변경 시)

---

## 9. EPIC 상세 내용

본 프로젝트는 총 18개의 EPIC으로 구성되어 있습니다. 각 EPIC 내에는 Story, Task, Test가 포함됩니다.

---

### EPIC 1. 딜 워크스페이스 + Deal Definition(정의 템플릿) 엔진

> **배경:** Completion accounts/locked box의 핵심은 "정의(Definitions) + 조정 메커니즘"입니다. WC/Net Debt는 거래별 정의가 필요하다는 점을 제품 구조로 고정해야 합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-101 | Story | **Deal 생성/버전/스냅샷** - 딜 단위로 데이터/정의/보고서가 버전 고정. DealType(Completion/LockedBox), 기준일, 통화, 기간 필수. 실행(run)마다 Snapshot ID + Definition Version ID + Engine Version 저장. 동일 조건 재실행 시 결과 해시 동일. |
| FDD-102 | Story | **Deal Definition 스키마 v1** - SPA/LOI 정의를 설정값으로 치환. Cash 정의, Debt 정의, debt-like/cash-like 카테고리, NWC 정의, Target NWC(peg) 산정, Lease liabilities(IFRS 16) 옵션 포함. |
| FDD-103 | Story | **Definition UI(편집/승인/잠금)** - 정의는 "작성자→리뷰어→승인" 워크플로우. 승인 이후 핵심 정의는 잠금. |
| FDD-104 | Task | **정의 템플릿 프리셋 6종** - 표준 CA, 표준 LB, 리스부채 포함형, deferred revenue debt-like 포함형, restricted cash 제외형, 하이브리드. |
| FDD-105 | Test | **정의 변경 회귀 시나리오 10종(골든)** - 10종 정의 변경 시 결과가 예상 방향과 불일치 0건. |

---

### EPIC 2. 데이터 인제스트(업로드) + 표준 입력 템플릿

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-201 | Story | **업로드 타입 자동감지(TB/GL/AR/AP/Bank/Debt/Lease)** - 자동감지 정확도 90% 이상(골든 파일 50개 기준). 오감지 시 사용자가 유형 선택 가능. |
| FDD-202 | Story | **필수 필드 검증기(스키마 밸리데이션)** - TB/GL 필수 필드 누락 시 누락 필드 목록 + 예시 + 업로드 거부. 금액 필드 문자열/통화 혼재 등 오류 탐지. |
| FDD-203 | Story | **대용량 GL 스트리밍 인제스트** - GL 100만 라인 기준 인제스트 완료 및 인덱싱 가능. 중복 전표ID/라인ID 탐지. |
| FDD-204 | Task | **입력 템플릿(엑셀) 배포본 6종 생성** - TB/GL/AR/AP/Bank/Debt(+Lease 옵션). 샘플 파일로 end-to-end 실행 가능. |
| FDD-205 | Test | **업로드 오류 케이스 30종** - 기간 누락, 통화 혼재, 마이너스/차대방향 오류, 중복 라인. 오류 메시지가 원인+수정방법 포함. |

---

### EPIC 3. 계정매핑(CoA Mapping) + Tie-out(재무제표 재구성) 엔진

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-301 | Story | **표준 라인아이템(Chart of Accounts Canon) v1** - Revenue/COGS/SG&A/Other OI/Non-operating/D&A, Cash, Debt, NWC-AR/AP/Inventory/Accruals 등. 최소 80개 표준 라인 지원. |
| FDD-302 | Story | **매핑 제안(반자동) + 승인 로그** - 매핑 신뢰도(High/Med/Low) 표시. 매핑 변경 시 영향 범위 리스트업. |
| FDD-303 | Story | **IS/BS 재구성 및 TB tie-out 리포트** - TB 합계와 재구성 IS/BS 불일치 시 불일치 계정 Top 20 자동 제시. tie-out 성공/실패가 품질 게이트로 저장. |
| FDD-304 | Task | **세그먼트(법인/사업부/지역) 다차원 지원 v1** - 필드 존재 시 자동 피벗 및 보고서에 세그먼트 뷰 생성(옵션). |
| FDD-305 | Test | **매핑/재구성 회귀 테스트(골든 20세트)** - 결과표(매출/EBITDA/총자산/부채/자본)가 골든과 정확 일치. |

---

### EPIC 4. Evidence Ledger(근거 원장) + 라인리지(Lineage)

> **배경:** 전자정보 분석 시 신뢰성 평가/증거 확보를 명확히 하려는 흐름이 있으므로, 보고서 자동생성도 "근거 강제"가 핵심입니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-401 | Story | **EvidenceLink 스키마 v1** - source_type(file/tb/gl/pdf), source_id, sheet/page, row/line, transaction_id, filter_hash, engine_version. 산출물 단위로 EvidenceLink 1개 이상 연결 가능. |
| FDD-402 | Story | **표 셀/행 단위 라인리지 생성** - QoE 조정항목 "행"마다 근거 링크 1개 이상. Net Debt/debt-like 스케줄 "항목"마다 근거 링크 1개 이상. |
| FDD-403 | Story | **근거 뷰어(원문 위치로 점프)** - GL: 전표ID 클릭 시 해당 라인 필터링 뷰. PDF: page/좌표 또는 최소 page로 이동. |
| FDD-404 | Task | **Evidence 누락 탐지기** - 보고서 생성 전 Evidence missing count가 0이 아니면 경고 + Draft 라벨 강제. |
| FDD-405 | Test | **Evidence 무결성 테스트** - 링크가 깨진 Evidence 0건, 필터 해시 불일치 0건. |

---

### EPIC 5. QoE(Adjusted EBITDA) 엔진 + 조정항목 후보 탐지

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-501 | Story | **Reported EBITDA 계산(표준) + 사용자 정의** - 표준 정의로 계산 가능(매핑 기반). 정의 변경 시 QoE 표 즉시 갱신. |
| FDD-502 | Story | **QoE Bridge(Reported→Adjusted) 자동 생성** - 브리지 합계 검증: Reported + ΣAdjustments = Adjusted (오차 0). 조정항목은 카테고리/상태/코멘트 포함. |
| FDD-503 | Story | **조정항목 후보 탐지(룰 기반 v1)** - 키워드(소송/구조조정/자문료), 계정 급증, 월말 대액 전표 등. 후보 0건이면 "후보 없음" 명시. |
| FDD-504 | Story | **이상치 스코어링(ML/통계/룰 혼합)** - 전표별 risk_score(0~100) 생성. 상위 N개 이상치 전표를 Appendix에 자동 첨부. |
| FDD-505 | Test | **QoE 회귀(골든 30케이스)** - Adjusted EBITDA 및 조정항목 합계가 골든과 정확 일치. |

---

### EPIC 6. NWC(운전자본) 엔진 + peg(정상수준) 시뮬레이션

> **배경:** WC는 고정 정의가 아니며(거래마다 정의), 정상수준 산정은 주관성이 크므로 "정의/시나리오/비교"가 제품 기능으로 고정되어야 합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-601 | Story | **NWC 정의 편집기(포함/제외/재분류)** - 계정/라인아이템을 NWC 포함/제외/기타로 드래그&드롭. cash/debt/debt-like 제외 옵션 제공(이중계산 방지). |
| FDD-602 | Story | **월별 NWC 트렌드 및 구성요소 분해** - AR/AP/Inventory/Other 구성요소가 월별로 분해되어 표 생성. |
| FDD-603 | Story | **peg 시나리오 6종** - 6M 평균, 12M 평균, TTM 평균, 최근3M 가중, 계절성 제외 평균, 사용자 지정 기간. 시나리오 변경 즉시 NWC Adjustment 재계산. |
| FDD-604 | Task | **계절성 플래그 룰 v1** - 월별 변동성이 특정 임계치 초과 시 "계절성 가능성" 경고. |
| FDD-605 | Test | **NWC 정의/시나리오 회귀 20세트** - 정의 변경에 따른 결과 변화가 예상 방향과 불일치 0건. |

---

### EPIC 7. Net Debt + debt-like/cash-like 엔진(분쟁 핵심)

> **배경:** debt-like(예: deferred revenue, factoring 등) 및 WC 경계는 분쟁 포인트로 반복 언급됩니다. 리스는 재무제표 및 성과표시에 영향을 미치므로 옵션/근거가 필요합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-701 | Story | **Net Debt 산식 엔진 v1** - Cash, Debt 정의에 따라 Net Debt 자동 산출(정의 변경 즉시 반영). |
| FDD-702 | Story | **debt-like 후보 탐지 룰셋 v1** - 미지급이자/수수료, 미지급세금, 거래비용, 관련자대여, deferred revenue, factoring. 항목마다 분류근거/EV 반영여부/현금유출시점/불확실성 필드 강제. |
| FDD-703 | Story | **deferred revenue(이연수익) 전용 시나리오** - (A) WC 포함 (B) debt-like 포함 (C) 제외 3시나리오 동시 비교표 자동 생성. |
| FDD-704 | Story | **리스부채(IFRS 16) 포함 옵션 + 영향 분석** - Lease liabilities 포함/제외 토글 시 Net Debt 및 브리지 영향 자동 갱신. 리스부채 근거 링크 필수. |
| FDD-705 | Test | **Net Debt/debt-like 회귀 25세트** - 스케줄 합계/분류 상태가 골든과 일치. |

---

### EPIC 8. Report Schema(IR) + Block 라이브러리(보고서 자동생성 핵심)

> **배경:** PPTX/DOCX는 OOXML 표준 문서이므로, "중간표현(IR)"을 정의하고 렌더러를 분리해야 템플릿/문서 유형 확장이 가능합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-801 | Story | **Report Schema v1 정의** - ReportMeta(딜명/기간/기준일/통화/정의버전/커버리지), Sections/Pages, Blocks(Text/Table/Chart/Issue/RequestList/Appendix), Claims + EvidenceLink. 스키마 JSON으로 저장/재사용 가능. |
| FDD-802 | Story | **Block: TableBlock v1** - QoE Bridge, QoE Adjustments Detail, NWC Definition, NWC Trend, NWC Peg Scenarios, Net Debt & debt-like schedule 등 최소 6종 지원. 테이블마다 표 헤더/단위/소계/합계/주석 표준 속성. |
| FDD-803 | Story | **Block: ChartBlock v1** - 매출/마진 트렌드, NWC 트렌드, Net Debt 브리지 등 최소 3종 지원. 차트는 표 데이터 스냅샷에서만 생성(직접 GL 참조 금지). |
| FDD-804 | Story | **Block: ClaimBlock(서술문) v1** - 문장(Claim)마다 EvidenceLink가 1개 이상 없으면 Unverified/Draft 자동 표기 또는 제외 정책 적용. |
| FDD-805 | Test | **Report Schema 호환성 테스트** - 동일 Schema로 PPT/Word 모두 생성 가능. |

---

### EPIC 9. PPTX 자동생성(Renderer) 1트랙: 생성형(Programmatic)

> **도구:** PptxGenJS는 JavaScript로 PPT 생성(테이블/텍스트/차트 등)을 지원합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-901 | Story | **PPT Renderer v1(최소 10장) — 고정 레이아웃** - 표지, Scope/Definitions, Executive Summary, QoE, NWC, Net Debt, Issue Log, Request List, Appendix, Methodology. IR 입력으로 PPTX 파일 생성. 모든 숫자 표는 Excel 데이터북과 일치. |
| FDD-902 | Story | **PPT Table 자동 레이아웃(오버플로우 처리)** - 행 수가 많으면 자동 분할(슬라이드 2장 이상). 텍스트 길이 초과 시 폰트 축소 또는 말줄임. 오버플로우 발생 시 검증 실패 처리 가능(엄격 모드). |
| FDD-903 | Story | **PPT 차트 삽입 v1(이미지 기반)** - ChartBlock 생성→PNG/SVG 생성→PPT 삽입. 차트 하단에 데이터 출처(표 이름/정의버전) 자동 표기. |
| FDD-904 | Story | **PPT 내 근거 인덱스(슬라이드별 Evidence Summary)** - 슬라이드마다 사용된 EvidenceLink 수/종류를 작은 표로 자동 삽입(외부배포본에서는 숨김 옵션). |
| FDD-905 | Test | **PPT 생성 회귀(골든 20세트)** - PPT 내 표 수치 diff 0건, 필수 슬라이드 누락 0건. |

---

### EPIC 10. PPTX 자동생성(Renderer) 2트랙: 템플릿 주입형

> **도구:** Open XML SDK는 Open XML 패키지/스키마 요소 조작을 단순화해 Office 문서 생성·조작을 지원합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1001 | Story | **Template Contract(placeholder 규칙) v1** - {{DEAL_NAME}}, {{PERIOD}}, {{DEFINITION_VERSION}}, {{TABLE:QOE_BRIDGE}}, {{CHART:NWC_TREND}} 등. 템플릿 검사기(placeholder 누락/중복/정의되지 않은 키 탐지). |
| FDD-1002 | Story | **PPT 템플릿 주입(Render) v1** - 고객 템플릿(.pptx) 업로드 후 placeholder에 값 주입. 폰트/마스터/색상은 템플릿을 유지. |
| FDD-1003 | Story | **템플릿별 스타일 토큰 매핑** - 단위 표기(원/백만원/억원), 소수점 자리, 표 테두리 스타일. Template Pack 변경 시에도 수치/근거는 동일, 서식만 변경. |
| FDD-1004 | Task | **템플릿 3종 파일럿(내부표준/고객A/고객B)** - 동일 Schema로 3종 템플릿 모두 생성 성공. |
| FDD-1005 | Test | **템플릿 주입 회귀 테스트** - placeholder 미치환 0건, 레이아웃 깨짐(오버플로우) 0건(엄격 모드). |

---

### EPIC 11. Word(DOCX) 보고서 자동생성(Renderer)

> **도구:** docxtpl은 docx 템플릿에 변수 바인딩, python-docx는 docx 생성/수정을 지원합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1101 | Story | **DOCX 템플릿(Word) v1 + docxtpl 주입** - IR→DOCX 생성(최소 15~25페이지 분량). 반복 테이블(조정항목 상세/전표 Top N) 자동 생성. |
| FDD-1102 | Story | **Word 표/스타일 표준화(Heading/Caption/Footnote)** - 표 제목/번호/주석 자동 관리(Word 기본 스타일 준수). |
| FDD-1103 | Story | **Word Appendix 자동 구성** - Appendix에 CoA 매핑표, QoE 상세, debt-like 상세, 커버리지/누락을 자동 삽입. |
| FDD-1104 | Task | **python-docx 보완 작업(템플릿 수정 불가능 영역)** - 머리말/바닥글, 메타데이터(작성일/버전) 강제 삽입. |
| FDD-1105 | Test | **DOCX 생성 회귀(골든 15세트)** - 표 수치 diff 0건, 섹션 누락 0건. |

---

### EPIC 12. Narrative Engine(서술문 자동생성) + Claim/Evidence 강제

> **배경:** 기술 보조 분석에서 "신뢰성 있는 증거 없이 결론" 리스크를 줄이려는 취지가 있으므로, 자동문장은 반드시 Claim-Evidence 구조로 통제해야 합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1201 | Story | **규칙 기반 Executive Summary 문장 생성 v1** - 단정 금지, 조건부 표현, 정의 버전 명시. 10개 기본 문장 템플릿 제공. 문장 수치는 표 데이터에서만 참조(직접 계산 금지). |
| FDD-1202 | Story | **Claim 객체화(문장=Claim) + Evidence 최소 1개 강제** - Evidence 0개인 Claim은 Unverified 라벨 또는 자동 제외. Claim 편집 시 변경로그 기록. |
| FDD-1203 | Story | **이슈로그 기반 자동 요약(Top N)** - Issue Log에서 근거 확정(verified) 상태만 요약에 포함. 영향 필드가 비어 있으면 "영향 미정" 명시. |
| FDD-1204 | Task | **문장 사전(용어/표현) 표준화** - 용어(Adjusted EBITDA, NWC, Net Debt, debt-like 등) 표기 일관성 검사기. |
| FDD-1205 | Test | **Claim/Evidence 누락 테스트** - Evidence 없는 Claim이 외부배포본에 포함되는 경우 0건. |

---

### EPIC 13. Chart Service(차트 생성) + 데이터-차트 정합성 검증

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1301 | Story | **차트 스펙(축/단위/기간/소스표) 정의** - 모든 차트는 소스표 이름, 정의버전, 단위를 메타로 포함. |
| FDD-1302 | Story | **차트 렌더러(서버 사이드) v1** - 동일 입력→동일 이미지(해시 동일). 차트 생성 실패 시 보고서 생성 실패 또는 대체 이미지+에러 배너 정책. |
| FDD-1303 | Story | **차트-표 데이터 검증** - 차트 값과 표 값 불일치 0건(자동 검증). |
| FDD-1304 | Task | **차트 3종 → 8종 확장** - EBITDA bridge waterfall, AR/AP aging 히트맵 등. |
| FDD-1305 | Test | **차트 회귀(골든 20세트)** - 차트 데이터 diff 0건(이미지 픽셀 diff가 아니라 데이터 diff 기준). |

---

### EPIC 14. Appendix + Evidence Index + 외부배포본 마스킹

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1401 | Story | **Evidence Index(슬라이드/페이지별 근거 목록) 생성** - 보고서 내 페이지/슬라이드 번호별 Evidence 목록 생성. Evidence 원천이 PDF인 경우 page 번호 포함. |
| FDD-1402 | Story | **외부배포본(External) 모드** - 전표ID/원문 링크/민감 필드 마스킹. Draft/Reviewed/Final 워터마크 자동. |
| FDD-1403 | Task | **내부검토본(Internal) 모드** - 내부용은 근거 링크/전표ID 표시(권한자만 열람). |
| FDD-1404 | Bug | **마스킹 예외 탐지(정규식/패턴)** - 주민번호/계좌번호/이메일 등 패턴 탐지 후 자동 마스킹. |
| FDD-1405 | Test | **외부배포본 민감정보 누출 테스트** - 탐지 규칙에 걸리는 문자열이 외부배포본에 남는 경우 0건. |

---

### EPIC 15. Delta Report(정의 변경 영향 리포트) — 협상/분쟁 대응용

> **배경:** WC/Net Debt/debt-like 정의 변경이 결과에 직접 영향을 주므로, 정의 변경의 정량 영향이 자동으로 비교되어야 합니다.

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1501 | Story | **정의 버전 간 Delta 계산 엔진** - (v1 vs v2) 비교 시 QoE/NWC/Net Debt 차이를 표로 자동 출력. |
| FDD-1502 | Story | **Delta Report PPT/DOCX 섹션 자동 삽입** - 정의 변경이 존재하는 경우에만 섹션이 자동 등장(없으면 숨김). |
| FDD-1503 | Story | **분쟁 민감 항목 자동 강조** - deferred revenue, restricted cash, lease liabilities, factoring. 민감 항목이 변경되면 "주의(Definition-sensitive)" 배지 자동 표시. |
| FDD-1504 | Task | **10개 대표 정의 변경 시나리오 라이브러리** - 클릭 1회로 시나리오 적용 및 Delta 생성. |
| FDD-1505 | Test | **Delta 정합성 테스트** - (v2 결과 - v1 결과) 합계가 Delta 표와 정확 일치. |

---

### EPIC 16. 회귀 테스트/골든 파일 + 자동 QA(보고서 품질 게이트)

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1601 | Story | **골든 데이터셋 50개 구축(익명화)** - 업로드 템플릿 6종 모두 포함하는 50세트 확보. |
| FDD-1602 | Story | **보고서 골든 테스트(표 수치 diff)** - PPT/Word 내 핵심 표 수치 diff 0건. |
| FDD-1603 | Story | **Layout QA(오버플로우/미치환 placeholder) 자동검사** - placeholder 미치환 0건, 테이블/텍스트 오버플로우 0건, 폰트 대체로 인한 줄바꿈 오류 감지. |
| FDD-1604 | Story | **Evidence QA(누락/깨짐) 자동검사** - Evidence missing / broken link 0건. |
| FDD-1605 | Story | **성능 회귀(대용량 GL)** - GL 100만 라인 기준 end-to-end SLA 충족 여부 자동 측정/리포트. |

---

### EPIC 17. 보안/감사추적/컴플라이언스 게이트

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1701 | Story | **RBAC(역할 기반 권한) v1** - 내부검토본(근거 포함) 다운로드는 권한자만. |
| FDD-1702 | Story | **감사로그(정의/매핑/문장/승인) v1** - 누가 어떤 Claim을 승인했는지 추적 가능. |
| FDD-1703 | Story | **데이터 보존/파기 정책 엔진** - 딜 종료 후 N일 보관/즉시 파기 등 정책 적용 가능. |
| FDD-1704 | Task | **보고서 메타데이터 스탬프(버전/해시/작성일)** - 보고서 속성(문서 메타) 및 표지에 자동 기재. |
| FDD-1705 | Test | **권한 우회/직접링크 접근 테스트** - 권한 없는 사용자가 내부근거에 접근 성공하는 케이스 0건. |

---

### EPIC 18. 운영(잡/큐/관측성) — 보고서 생성은 파이프라인으로 관리

| 이슈 ID | 유형 | 목표 및 수용기준(AC) |
|---------|------|----------------------|
| FDD-1801 | Story | **Report Generation Job 오케스트레이션** - validate→compute→schema build→render ppt/docx→package→qa gate→publish. 각 단계 실패 시 원인 코드/재시도 정책 기록. |
| FDD-1802 | Story | **실행 로그/메트릭(품질 스코어 포함)** - 커버리지 점수, tie-out 성공 여부, evidence 누락 수, 오버플로우 수가 run 메타에 저장. |
| FDD-1803 | Task | **실패 리포트(사용자용) 자동 생성** - 실패 시 어떤 입력/정의/단계에서 무엇이 실패했는지 사람이 읽을 수 있게 출력. |
| FDD-1804 | Bug | **재시도 시 중복 산출 방지(idempotency)** - 동일 job_id 재시도해도 결과 패키지 1개만 final. |
| FDD-1805 | Test | **장애 주입(Chaos) 10종** - 장애 상황에서도 데이터 무결성/로그 일관성 유지. |

---

## 10. 우선순위 및 최소 경로 (MVP)

다음 19개 Story가 "보고서 자동생성 end-to-end" 최소 경로입니다. 이것부터 스프린트에 배치하는 것을 권장합니다.

### 10.1 MVP 필수 Story (19개)

| 이슈 ID | EPIC | 설명 |
|---------|------|------|
| FDD-101 | EPIC 1 | Deal 생성/버전/스냅샷 |
| FDD-102 | EPIC 1 | Deal Definition 스키마 v1 |
| FDD-201 | EPIC 2 | 업로드 타입 자동감지 |
| FDD-202 | EPIC 2 | 필수 필드 검증기 |
| FDD-301 | EPIC 3 | 표준 라인아이템(CoA Canon) v1 |
| FDD-302 | EPIC 3 | 매핑 제안(반자동) + 승인 로그 |
| FDD-303 | EPIC 3 | IS/BS 재구성 및 TB tie-out 리포트 |
| FDD-401 | EPIC 4 | EvidenceLink 스키마 v1 |
| FDD-402 | EPIC 4 | 표 셀/행 단위 라인리지 생성 |
| FDD-502 | EPIC 5 | QoE Bridge 자동 생성 |
| FDD-602 | EPIC 6 | 월별 NWC 트렌드 및 구성요소 분해 |
| FDD-701 | EPIC 7 | Net Debt 산식 엔진 v1 |
| FDD-702 | EPIC 7 | debt-like 후보 탐지 룰셋 v1 |
| FDD-801 | EPIC 8 | Report Schema v1 정의 |
| FDD-802 | EPIC 8 | Block: TableBlock v1 |
| FDD-901 | EPIC 9 | PPT Renderer v1 (최소 10장) |
| FDD-1602 | EPIC 16 | 보고서 골든 테스트(표 수치 diff) |
| FDD-1603 | EPIC 16 | Layout QA 자동검사 |
| FDD-1604 | EPIC 16 | Evidence QA 자동검사 |

### 10.2 후속 개발 순서

1. **차트 서비스 (EPIC 13)** - Chart Service + 데이터-차트 정합성 검증
2. **Word 보고서 (EPIC 11)** - DOCX 자동생성
3. **템플릿 주입형 PPT (EPIC 10)** - 고객 템플릿 유지 기능
4. **Delta Report (EPIC 15)** - 정의 변경 영향 리포트

---

## 11. 개발 착수 전 최종 체크리스트

기존 마스터파일 체크리스트(12개) + v2 보완사항(30개) = **총 42개 항목**

### 11.1 규칙(Rules) 체크리스트

| No. | 항목 | 상태 |
|-----|------|------|
| R1 | Python 코딩 표준 (Black + Ruff + mypy) 설정 | ☐ |
| R2 | TypeScript/React 코딩 표준 확립 | ☐ |
| R3 | DB 네이밍 규칙 및 마이그레이션 정책 확정 | ☐ |
| R4 | Git 브랜치 전략 및 커밋 규칙 합의 | ☐ |
| R5 | 코드 리뷰 프로세스 (PR 규칙) 확정 | ☐ |
| R6 | 테스트 커버리지 목표 및 필수 대상 정의 | ☐ |
| R7 | 에러 코드 체계 설계 | ☐ |
| R8 | 로깅 표준 (구조화 로그, 개인정보 마스킹) 확정 | ☐ |
| R9 | 금액 처리 규칙 (Decimal, 라운딩, 환율) 확정 | ☐ |
| R10 | Deal Definition 변경 시 영향 처리 규칙 확정 | ☐ |

### 11.2 스킬(Skills) 체크리스트

| No. | 항목 | 상태 |
|-----|------|------|
| S1 | 기술 스택 최종 확정 (Python 3.12 + FastAPI + React + Vite + PostgreSQL) | ✅ |
| S2 | 프로젝트 폴더 구조 생성 및 보일러플레이트 세팅 | ✅ |
| S3 | Excel 파서 프로토타입 (TB/GL 최소 2종) | ☐ |
| S4 | CoA 매핑 알고리즘 PoC (정확매치 + 유사매치) | ☐ |
| S5 | 이상치 탐지 알고리즘 PoC (Z-score + Isolation Forest) | ☐ |
| S6 | API 엔드포인트 설계서 작성 (OpenAPI/Swagger) | ☐ |
| S7 | DB 스키마 생성 및 Alembic 초기 마이그레이션 | ✅ |
| S8 | Docker Compose 개발 환경 구축 | ✅ |
| S9 | CI/CD 파이프라인 기본 설정 (GitHub Actions) | ☐ |
| S10 | 모니터링 기본 설정 (Grafana + Sentry) | ☐ |

### 11.3 에이전트(Agent) 체크리스트

| No. | 항목 | 상태 |
|-----|------|------|
| A1 | 에이전트 역할 분담 및 상호작용 흐름 확정 | ☐ |
| A2 | LLM 사용 범위 확정 (계산은 룰, 판단 지원만 LLM) | ☐ |
| A3 | QoE Analyzer Agent 프롬프트 v1.0 작성 | ☐ |
| A4 | CoA Mapper Agent 프롬프트 v1.0 작성 | ☐ |
| A5 | Contract Analyzer Agent 프롬프트 v1.0 작성 | ☐ |
| A6 | Structured Output JSON 스키마 전체 정의 | ☐ |
| A7 | LLM Guardrails 구현 (금액 교차검증, 할루시네이션 탐지) | ☐ |
| A8 | 프롬프트 버전관리 체계 구축 | ☐ |
| A9 | LLM 비용 모니터링 대시보드 설계 | ☐ |
| A10 | 에이전트 A/B 테스트 프레임워크 설계 | ☐ |

### 11.4 기존 마스터파일 체크리스트 (재확인)

| No. | 항목 | 상태 |
|-----|------|------|
| M1 | 표준 산출물 템플릿 3종 확정 (QoE/NWC/Net Debt) | ☐ |
| M2 | LOI/SPA 정의를 설정 파라미터로 모델링 | ☐ |
| M3 | 입력 데이터 최소셋(TB+GL+Aging)으로 MVP 설계 | ☐ |
| M4 | Canonical Data Model 스키마 고정 | ☐ |
| M5 | 계정매핑(CoA mapping) UX 설계 (반자동+승인) | ☐ |
| M6 | Evidence Ledger 스키마 설계 | ☐ |
| M7 | QoE add-back 후보: 제안만, 최종은 승인 잠금 | ☐ |
| M8 | Debt-like item 룰 seed list 구축 | ☐ |
| M9 | IFRS 15/16 문서 추출 스키마 준비 | ☐ |
| M10 | 보안/국외이전 설계 (PIPA 요건) | ☐ |
| M11 | 베타 파일럿 파트너 2-3곳 확보 | ☐ |
| M12 | 약관/리포트 면책 문구 작성 | ☐ |

> **총 체크리스트: Rules 10개 + Skills 10개 + Agent 10개 + 기존 12개 = 42개 항목**
> S1, S2, S7, S8은 Sprint 1에서 완료됨.

---

## 12. 참고 문헌 및 전거

### 12.1 FDD/M&A 관련

- Completion mechanism에서 Working Capital이 법적/IFRS상 정의가 아니며, 거래별 정의 및 분쟁 포인트(예: debt-like 항목 등)를 다루는 가이드
- FDD 수행의 목적/범위/산출물 및 기술(예: AI) 변화 언급이 포함된 ICAEW FDD 가이드
- 기술 보조 분석(technology-assisted analysis) 사용 시 신뢰성 있는 증거 확보/문서화 책임을 명확히 하려는 PCAOB 공지 및 요약

### 12.2 기술/도구 관련

- OOXML 표준(ECMA-376) 및 Open XML SDK (OOXML 조작)
- PPT 생성 라이브러리(PptxGenJS) 문서
- Word 템플릿 기반 생성(docxtpl) 및 python-docx

### 12.3 회계/재무 관련

- 리스(IFRS 16) 효과 분석 자료 (리스부채/재무제표 영향 맥락)
- 전표 전수 분석/리스크 스코어링 벤치마크 (MindBridge 메모)
- 문서 추출/교차검증 워크플로우 벤치마크 (DataSnipper)

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| 문서명 | FDD 자동화 개발계획 로드맵 마스터파일 |
| 버전 | 2.0 (v2 통합) |
| 작성일 | 2026. 2. 5. |
| 개정일 | 2026. 2. 5. |
| 적용 범위 | Completion Accounts / Locked Box 모두 지원 |
| 아키텍처 | 옵션 3: Python Backend + React Frontend |
| 총 EPIC 수 | 18개 |
| 총 이슈 수 | 90개 (Story/Task/Test/Bug) |
| 체크리스트 | 42개 항목 (Rules 10 + Skills 10 + Agent 10 + 기존 12) |
