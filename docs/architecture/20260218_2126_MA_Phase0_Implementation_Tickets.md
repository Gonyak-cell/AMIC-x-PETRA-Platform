# M&A 플랫폼 전환 — Phase 0 구현 계획 (상세 티켓)

**작성일**: 2026-02-18 21:24
**브랜치**: `feat/ma-workflow`
**참조 문서**: `docs/architecture/20260217_2304_MA_Workflow_Implementation_Plan.md`
**구현 범위**: Phase 0만 우선 구현, Phase 1은 검증 후 별도 진행
**DB 패턴 결정**: 비동기(async) SQLAlchemy — KIIS/IM 패턴 채택

---

## Context

AMIC Platform을 "분석 도구 모음"에서 **7단계 M&A 거래 관리 플랫폼**으로 전환한다. 핵심은 새로운 `deal-mgmt` 백엔드 서비스(port 8003)를 신설하고, 프론트엔드에 `/ma/*` 모듈을 추가하며, 기존 FDD/IM/KIIS 서비스를 API 호출로 연동하는 것이다.

**현재 상태**: FDD(:8000) + KIIS(:8001) + IM(:8002) 3개 독립 서비스, React 프론트엔드
**목표 상태**: deal-mgmt(:8003) 마스터 서비스가 7단계 워크플로우를 관장, FDD/IM/KIIS는 하위 서비스

**이번 구현 (Phase 0)**: 기반 인프라 — deal-mgmt 스캐폴딩, Docker, 프록시, FE 모듈 셸, 인증, CI/CD

---

## 병렬 작업 그룹 총괄

```text
═══════════════════════════════════════════════════════════════
 PHASE 0: 기반 구축 (Week 1~2) — 6개 병렬 그룹
═══════════════════════════════════════════════════════════════
  그룹 P0-A: 백엔드 스캐폴딩     ─┐
  그룹 P0-B: Docker 인프라       ─┤── 병렬 실행
  그룹 P0-C: 프록시 레이어       ─┤   (P0-B, P0-C는 P0-A 완료 후)
  그룹 P0-D: 프론트엔드 기반     ─┤── 독립적 병렬
  그룹 P0-E: 인증 통합           ─┤── P0-A 완료 후
  그룹 P0-F: CI/CD 업데이트      ─┘── P0-B 완료 후
```

---

## PHASE 0: 기반 구축 (13개 티켓)

### 그룹 P0-A: 백엔드 서비스 스캐폴딩 (순차)

#### P0-A1: deal-mgmt 서비스 초기화

- **설명**: FastAPI 비동기 서비스 스켈레톤 생성 (KIIS 패턴 기반)
- **복잡도**: M
- **의존성**: 없음
- **생성 파일**:
  - `deal-mgmt/app/main.py` — FastAPI 앱 + lifespan + CORS + `/health`
  - `deal-mgmt/app/core/config.py` — `Settings(BaseSettings)`: DATABASE_URL, JWT_SECRET, FDD/IM/KIIS_API_URL
  - `deal-mgmt/app/core/database.py` — async engine + `async_sessionmaker` + `get_db()`
  - `deal-mgmt/app/core/security.py` — `JWTClaims` dataclass + `get_jwt_claims()` (KIIS 패턴)
  - `deal-mgmt/app/core/exceptions.py` — HTTPException 핸들러
  - `deal-mgmt/app/models/base.py` — `Base(DeclarativeBase)` + `TimestampMixin`
  - `deal-mgmt/pyproject.toml` — fastapi, sqlalchemy[asyncio], asyncpg, httpx, alembic
  - `deal-mgmt/Dockerfile` — multi-stage, python:3.12-slim, non-root user
  - `deal-mgmt/alembic.ini` + `deal-mgmt/alembic/env.py`
  - `deal-mgmt/tests/conftest.py`
- **검증**: `uvicorn app.main:app --port 8003` → `GET /health` 200 OK
- **참조**: `kiis/app/core/database.py`, `kiis/app/core/security.py`

#### P0-A2: 도메인 Enum + 기본 모델 정의

- **설명**: M&A 도메인 열거형 8종 + AuditLog 모델
- **복잡도**: M
- **의존성**: P0-A1
- **생성 파일**:
  - `deal-mgmt/app/models/enums.py`:
    - `TransactionSide` (SELL, BUY, DUAL)
    - `TransactionPhase` (ENGAGEMENT → POST_CLOSING, 7단계)
    - `TransactionStatus` (DRAFT, ACTIVE, ON_HOLD, COMPLETED, TERMINATED)
    - `EngagementType` (EXCLUSIVE, NON_EXCLUSIVE, CO_ADVISORY)
    - `WorkingGroupRole` (LEAD_ADVISOR, LEGAL_COUNSEL 등 7종)
    - `BuyerCandidateStatus` (IDENTIFIED → SELECTED/REJECTED, 14단계)
    - `BuyerType` (STRATEGIC, FINANCIAL_SPONSOR 등)
    - `AuditAction` (CREATE, UPDATE, PHASE_TRANSITION 등)
  - `deal-mgmt/app/models/audit.py` — AuditLog (UUID PK, entity_type, JSONB old/new_value)
- **검증**: import 성공, ruff check 통과

#### P0-A3: 핵심 ORM 모델 + Alembic 마이그레이션

- **설명**: Transaction, Engagement, WorkingGroupMember, BuyerCandidate, DealTimeline 모델
- **복잡도**: L
- **의존성**: P0-A2
- **생성 파일**:
  - `deal-mgmt/app/models/transaction.py` — Transaction (UUID PK, code_name unique, side, phase, status, target fields, financial fields, fdd/im links, soft-delete)
  - `deal-mgmt/app/models/engagement.py` — Engagement (transaction FK, type, fee_structure JSONB, signed_at)
  - `deal-mgmt/app/models/working_group.py` — WorkingGroupMember (transaction FK, name, email, role, is_active)
  - `deal-mgmt/app/models/buyer_candidate.py` — BuyerCandidate (transaction FK, status pipeline, ioi/loi values, metadata JSONB)
  - `deal-mgmt/app/models/timeline.py` — DealTimeline (transaction FK, event_type, event_date)
  - `deal-mgmt/alembic/versions/001_initial_schema.py`
- **검증**: `alembic upgrade head` 성공, `alembic downgrade base` 클린 드롭
- **참조**: `fdd/backend/app/models/deal.py` (UUID PK, enum, soft-delete 패턴)

---

### 그룹 P0-B: Docker 인프라 (P0-A1 완료 후)

#### P0-B1: Docker Compose에 deal-mgmt 서비스 추가

- **설명**: deal-mgmt-api + deal-mgmt-db를 docker-compose에 추가
- **복잡도**: M
- **의존성**: P0-A1
- **수정 파일**:
  - `docker-compose.yml` — deal-mgmt-db (postgres:16-alpine, port 5436:5432), deal-mgmt-api (build ./deal-mgmt, port 8003:8000)
  - `docker-compose.prod.yml` — production overrides (no host ports, 2G limit, uvicorn --workers 4)
  - `.env.production.example` — MA_DB_PASSWORD, MA_CORS_ORIGINS 추가
- **검증**: `docker compose up deal-mgmt-api deal-mgmt-db` → health OK

---

### 그룹 P0-C: 프록시 레이어

#### P0-C1: Nginx dev/prod 프록시 추가

- **설명**: `/api/ma/*` → deal-mgmt-api 프록시 규칙 추가
- **복잡도**: S
- **의존성**: P0-B1
- **수정 파일**:
  - `nginx/dev.conf` — upstream deal_mgmt_api, location /api/ma/
  - `nginx/prod.conf` — 동일 (SSL 서버 블록 내)
  - `nginx/prod-nossl.conf` — 동일
- **검증**: `curl http://localhost:3000/api/ma/health` → 200

#### P0-C2: Vite dev 프록시 추가

- **설명**: 프론트엔드 개발 서버 프록시에 `/api/ma` 추가
- **복잡도**: S
- **의존성**: 없음
- **수정 파일**:
  - `amic-platform/vite.config.ts` — /api/ma/health, /api/ma 프록시 추가
- **검증**: Vite dev 서버 정상 시작, 기존 프록시 무영향

---

### 그룹 P0-D: 프론트엔드 기반 (독립적, 즉시 시작 가능)

#### P0-D1: MA API 클라이언트 생성

- **설명**: `createApiClient("/api/ma")` 패턴으로 maApi 생성
- **복잡도**: S
- **의존성**: 없음
- **생성 파일**:
  - `amic-platform/src/api/maClient.ts`
- **참조**: `src/api/fddClient.ts`

#### P0-D2: MA 타입 정의

- **설명**: 전체 MA 도메인 TypeScript 타입 (union literal, NOT enum)
- **복잡도**: M
- **의존성**: 없음
- **생성 파일**:
  - `src/modules/ma/types/transaction.ts`
  - `src/modules/ma/types/engagement.ts`
  - `src/modules/ma/types/buyer.ts`
  - `src/modules/ma/types/workflow.ts`
  - `src/modules/ma/types/timeline.ts`
- **검증**: `tsc --noEmit` 에러 0
- **참조**: `src/modules/fdd/types/deal.ts`

#### P0-D3: MA 상수 + MaRoutes.tsx 라우트 셸

- **설명**: SelectOption 배열, Phase 설정, 라우트 정의
- **복잡도**: S
- **의존성**: P0-D2
- **생성 파일**:
  - `src/modules/ma/constants.ts`
  - `src/modules/ma/MaRoutes.tsx`
- **참조**: `src/modules/fdd/constants.ts`, `FddRoutes.tsx`

#### P0-D4: App.tsx 라우트 등록 + Sidebar + ModuleSwitcher

- **설명**: /ma/* 라우트, Sidebar M&A 네비게이션, ModuleSwitcher 추가
- **복잡도**: M
- **의존성**: P0-D3
- **수정 파일**:
  - `src/App.tsx`
  - `src/components/layout/Sidebar.tsx`
  - `src/components/layout/ModuleSwitcher.tsx`
- **검증**: /ma 접근 시 MA 모듈 로드, ModuleSwitcher에 4개 모듈

#### P0-D5: Dashboard M&A 위젯 통합

- **설명**: M&A KPI 카드, Quick Action, 모듈 카드, 헬스체크 추가
- **복잡도**: M
- **의존성**: P0-D1
- **수정 파일**:
  - `src/hooks/useDashboard.ts`
  - `src/hooks/useHealthCheck.ts`
  - `src/pages/DashboardPage.tsx`
- **검증**: deal-mgmt 다운 시 다른 KPI 미차단

---

### 그룹 P0-E: 인증 통합 (P0-A1 완료 후)

#### P0-E1: deal-mgmt JWT 인증 연동

- **설명**: FDD 발급 JWT를 deal-mgmt에서 검증 (공유 JWT_SECRET)
- **복잡도**: M
- **의존성**: P0-A1
- **생성 파일**:
  - `deal-mgmt/app/auth/dependencies.py`
  - `deal-mgmt/app/auth/jwt.py`
- **검증**: FDD 로그인 → deal-mgmt API 인증 성공, 토큰 없으면 401
- **참조**: `kiis/app/core/security.py`

---

### 그룹 P0-F: CI/CD 업데이트 (P0-B1 완료 후)

#### P0-F1: CI 파이프라인 + 배포 스크립트 업데이트

- **설명**: deal-mgmt 테스트/빌드/배포를 CI와 스크립트에 추가
- **복잡도**: S
- **의존성**: P0-B1
- **수정 파일**:
  - `.github/workflows/ci.yml`
  - `.github/workflows/deploy.yml`
  - `scripts/health-check.ps1`
  - `scripts/dev-up.ps1`, `scripts/dev-down.ps1`

---

## Phase 0 병렬 실행 다이어그램

```text
Week 1:
  P0-A1 ──→ P0-A2 ──→ P0-A3          (백엔드: 순차)
  P0-D1 ──→ P0-D5                     (FE API + 대시보드: 독립)
  P0-D2 ──→ P0-D3 ──→ P0-D4          (FE 타입/라우트/사이드바: 독립)
  P0-C2                                (Vite 프록시: 독립)

Week 2 (P0-A1 완료 후):
  P0-B1                                (Docker: A1 의존)
  P0-E1                                (인증: A1 의존)

Week 2 (P0-B1 완료 후):
  P0-C1                                (Nginx: B1 의존)
  P0-F1                                (CI/CD: B1 의존)
```

---

## Phase 0 티켓 요약

| 그룹 | 티켓 | 복잡도 | 의존성 |
| :--- | :--- | :---: | :--- |
| P0-A | P0-A1: 서비스 초기화 | M | 없음 |
| P0-A | P0-A2: Enum + AuditLog | M | P0-A1 |
| P0-A | P0-A3: ORM 모델 + Alembic | L | P0-A2 |
| P0-B | P0-B1: Docker Compose | M | P0-A1 |
| P0-C | P0-C1: Nginx 프록시 | S | P0-B1 |
| P0-C | P0-C2: Vite 프록시 | S | 없음 |
| P0-D | P0-D1: maClient.ts | S | 없음 |
| P0-D | P0-D2: 타입 정의 (5파일) | M | 없음 |
| P0-D | P0-D3: 상수 + 라우트 | S | P0-D2 |
| P0-D | P0-D4: App/Sidebar/Switcher | M | P0-D3 |
| P0-D | P0-D5: Dashboard 위젯 | M | P0-D1 |
| P0-E | P0-E1: JWT 인증 | M | P0-A1 |
| P0-F | P0-F1: CI/CD | S | P0-B1 |

**총 13개 티켓** — S: 4개, M: 7개, L: 1개

---

## 수정 대상 기존 파일

| 파일 | 변경 내용 | 티켓 |
| :--- | :--- | :--- |
| `docker-compose.yml` | deal-mgmt-api + deal-mgmt-db 추가 | P0-B1 |
| `docker-compose.prod.yml` | production overrides | P0-B1 |
| `nginx/dev.conf` | /api/ma/ 프록시 | P0-C1 |
| `nginx/prod.conf` | /api/ma/ 프록시 (SSL) | P0-C1 |
| `nginx/prod-nossl.conf` | /api/ma/ 프록시 | P0-C1 |
| `amic-platform/vite.config.ts` | /api/ma 프록시 | P0-C2 |
| `amic-platform/src/App.tsx` | /ma/* 라우트 | P0-D4 |
| `amic-platform/src/components/layout/Sidebar.tsx` | M&A 네비게이션 | P0-D4 |
| `amic-platform/src/components/layout/ModuleSwitcher.tsx` | M&A 모듈 | P0-D4 |
| `amic-platform/src/pages/DashboardPage.tsx` | M&A KPI + 카드 | P0-D5 |
| `amic-platform/src/hooks/useDashboard.ts` | M&A 쿼리 추가 | P0-D5 |
| `amic-platform/src/hooks/useHealthCheck.ts` | M&A 헬스체크 | P0-D5 |
| `.env.production.example` | MA 환경변수 | P0-B1 |

## 핵심 참조 파일 (패턴 재사용)

| 참조 파일 | 재사용 패턴 |
| :--- | :--- |
| `kiis/app/core/database.py` | async SQLAlchemy 세션 팩토리 |
| `kiis/app/core/security.py` | 크로스 백엔드 JWT 페더레이션 |
| `fdd/backend/app/models/deal.py` | UUID PK, enum, soft-delete, JSONB |
| `src/api/fddClient.ts` | createApiClient 팩토리 (2줄) |
| `src/modules/fdd/hooks/useDeals.ts` | TanStack Query 훅 패턴 |
| `src/modules/fdd/FddRoutes.tsx` | lazy-loaded 라우트 정의 |
| `src/modules/fdd/pages/DealWorkspacePage.tsx` | 워크스페이스 셸 (중첩 라우트) |

---

## Phase 1 참조 (다음 구현)

Phase 1 상세 티켓은 `hidden-baking-garden.md` 계획 파일에 포함. 4개 병렬 스트림(20개 티켓):

- 스트림 1: Transaction CRUD + 워크플로우 엔진 (7 티켓)
- 스트림 2: Engagement + WGL + 이해충돌 (4 티켓)
- 스트림 3: Buyer 파이프라인 + 서비스 연동 (5 티켓)
- 스트림 4: 타임라인 + 대시보드 KPI (4 티켓)
