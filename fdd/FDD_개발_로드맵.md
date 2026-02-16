# FDD 자동화 프로젝트 — 개발 로드맵

> 최종 업데이트: 2026년 02월 10일 18시 32분 37초
> 마스터파일 버전: 2.6 (Sprint 16 완료 — Multi-Entity + Multi-Currency 연결 분석 + 1,303 tests)

---

## 전체 타임라인 개요

```
Sprint 1  ████████████████ COMPLETE
Sprint 2  ████████████████ COMPLETE
Sprint 3  ████████████████ COMPLETE
Sprint 4  ████████████████ COMPLETE (100%)
Sprint 5  ████████████████ COMPLETE (100%)
Sprint 6  ████████████████ COMPLETE — 이상치 탐지 + AI Agent v1 (595 tests)
Sprint 7  ████████████████ COMPLETE — Report Schema + PPT 생성 (622 tests)
Sprint 8  ████████████████ COMPLETE — 품질 게이트 + 회귀 테스트 (775 tests)
Sprint 9  ████████████████ COMPLETE — Word 보고서 + 차트 서비스 (881 tests)
Sprint 10 ████████████████ COMPLETE — 템플릿 주입 + Delta Report (993 tests)
Sprint 11 ████████████████ COMPLETE — 보안/감사 + 운영 (1,155 tests)
Sprint 12 ████████████████ COMPLETE — 통합 테스트 + 베타 릴리즈 (1,175 tests + E2E 39)
Sprint 13 ████████████████ COMPLETE — Production Hardening + FDD Workflow
Sprint 14 ████████████████ COMPLETE — 기술부채 해소 (Multi-LLM + BaseAgent)
Sprint 15 ████████████████ COMPLETE — Testcontainers 마이그레이션 (1,209 tests)
Sprint 16 ████████████████ COMPLETE — Multi-Entity + Multi-Currency 연결 분석 (1,303 tests)
```

---

## Phase 1: 기반 구축 (Sprint 1~3)

### Sprint 1: 프로젝트 스캐폴딩 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | 프로젝트 기반 구조 + Deal/Definition/Snapshot 모델 + 기본 API + Frontend 페이지 |
| EPIC | EPIC 1 (부분) |
| 상태 | **완료** |

**완료 항목:**
- FastAPI + SQLAlchemy + Alembic 백엔드 구축
- React 19 + Vite + TanStack Query 프론트엔드 구축
- PptxGenJS Node.js sidecar (pptx-service) 구축
- Docker Compose 개발 환경
- Deal CRUD API (`/api/v1/deals`)
- DealDefinition, Snapshot 모델 + 해싱
- AuditLog 모델
- DealListPage, DealWorkspacePage, DefinitionPage
- 단위 테스트 (conftest.py + test_deals + test_hashing)

---

### Sprint 2: 데이터 인제스트 + 표준 입력 템플릿 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | Excel 업로드 → 파싱 → 검증 → DB 저장 파이프라인 |
| EPIC | EPIC 2 |
| MVP Story | FDD-201, FDD-202 |
| 상태 | **완료 (100%)** |

**완료 항목:**
- [x] Excel 파서 (openpyxl streaming): TB/GL 등 7종 자동감지
- [x] 업로드 타입 자동감지 — 점수 기반 7종 분류 (FDD-201)
- [x] 필수 필드 검증기 — VAL-000~VAL-011 12개 규칙 (FDD-202)
- [x] 대용량 GL 스트리밍 인제스트 — read_only + 5000행 배치 (FDD-203)
- [x] 입력 템플릿 6종 생성 — `templates/input_samples/` (FDD-204)
- [x] 업로드 API — 5개 엔드포인트 (upload/list/detail/confirm-type/ingest)
- [x] Frontend: 업로드 탭 UI — 드래그&드롭, 진행바, 검증 결과 표시 (354줄)
- [x] 업로드 오류 케이스 테스트 48종 (FDD-205) — 목표 30 초과 달성 (uploads 20 + validator 23 + detector 5)

**산출물:** 데이터 파이프라인 MVP ✅, 입력 템플릿 6종 ✅

---

### Sprint 3: CoA 매핑 + Tie-out + Evidence Ledger — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | 계정매핑 → 재무제표 재구성 + 근거 추적 기반 |
| EPIC | EPIC 3, EPIC 4 |
| MVP Story | FDD-301, FDD-302, FDD-303, FDD-401, FDD-402 |
| 상태 | **완료 (100%)** — LLM 매핑은 Sprint 6 범위 |

**완료 항목:**
- [x] 표준 라인아이템 (CoA Canon) v1 — 80개 표준 라인 + 시드 (FDD-301)
- [x] 매핑 제안 (반자동) + 승인 로그 — exact/keyword/fuzzy 3단계 (FDD-302)
- [x] IS/BS 재구성 및 TB tie-out 리포트 (FDD-303)
- [x] EvidenceLink 스키마 v1 + API 6 endpoints (FDD-401)
- [x] 표 셀/행 단위 라인리지 생성 — ledger CRUD + detector (FDD-402)
- [x] 매핑 API (10 endpoints) + Evidence API (6 endpoints)
- [x] Frontend: MappingPage — Auto-Suggest → Save → Approve 워크플로 + Tie-out 결과
- [x] 골든 회귀 테스트 — 20개 시나리오 + 4개 E2E (FDD-305)
- [x] 테스트: 169개 ALL PASS (12 파일, 1.91s)
- [x] Frontend lint/tsc 검증 — strict 모드 전체 ON, 타입 에러 없음 확인

**산출물:** 매핑 엔진 ✅, EvidenceLink 기반 ✅, tie-out 품질 게이트 ✅

---

## Phase 2: 분석 엔진 (Sprint 4~6)

### Sprint 4: QoE(Adjusted EBITDA) 엔진 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | EBITDA 계산 + QoE Bridge + 조정항목 후보 탐지 |
| EPIC | EPIC 5 |
| MVP Story | FDD-502 |
| 상태 | **완료 (100%)** |

**완료 항목:**
- [x] Reported EBITDA 계산 (표준 + 사용자 정의) (FDD-501) — `qoe_engine.py` calculate_reported_ebitda()
- [x] QoE Bridge 자동 생성 (FDD-502) — build_qoe_bridge(), 서비스+API+Frontend
- [x] 조정항목 후보 탐지 (룰 기반 v1) (FDD-503) — 4개 룰 (keyword/non_operating/year_end/large_entry)
- [x] QoE 계산 엔진 (`engines/qoe_engine.py`) — 순수 함수, ENGINE_VERSION="0.1.0"
- [x] QoE 서비스 (`services/qoe/qoe_service.py`) — run/recalculate/CRUD 7개 함수
- [x] QoE API (`/api/v1/deals/{id}/qoe/*`) — 8개 엔드포인트
- [x] QoE Pydantic 스키마 7개
- [x] Frontend: QoEPage.tsx (EBITDA 요약 + 브리지 표 + 조정후보 테이블), useQoE.ts 8개 훅, qoe.ts 타입
- [x] 골든 회귀 테스트 30케이스 (FDD-505) + 엔진 25개 + API 9개 = 64 QoE 테스트

**산출물:** QoE 엔진 v1 ✅, 브리지 자동 생성 ✅

---

### Sprint 5: NWC + Net Debt 엔진 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | NWC 트렌드/peg 시뮬레이션 + Net Debt/debt-like 엔진 |
| EPIC | EPIC 6, EPIC 7 |
| MVP Story | FDD-602, FDD-701, FDD-702 |
| 상태 | **완료 (100%)** |

**완료 항목:**
- [x] NWC 정의 편집기 (FDD-601) — classify_nwc_items(), NWCDefinition, update_line_item_classification
- [x] 월별 NWC 트렌드 및 구성요소 분해 (FDD-602) — calculate_nwc() monthly_trend, NWC API summary
- [x] peg 시나리오 6종 (FDD-603) — calculate_peg(), simulate_all_pegs(), peg-simulate API
- [x] Net Debt 산식 엔진 v1 (FDD-701) — calculate_net_debt(), Adjusted Net Debt 공식, balance_check
- [x] debt-like 후보 탐지 룰셋 v1 (FDD-702) — detect_debt_like_candidates() 3 rules (lease/keyword/deferred)
- [x] deferred revenue 시나리오 (FDD-703) — DebtOptions(include_deferred_revenue=True)
- [x] 리스부채(IFRS 16) 옵션 (FDD-704) — DebtOptions(include_lease_liabilities=True), IFRS16 warning
- [x] NWC API 7ep + Debt API 8ep — 전체 엔드포인트 구현
- [x] NWC 스키마 8개 + Debt 스키마 7개
- [x] Frontend: NWCPage.tsx (482줄) + NetDebtPage.tsx (526줄) + useNWC.ts (7훅) + useDebt.ts (8훅) + nwc.ts/debt.ts 타입
- [x] Workspace 라우팅 — NWC/Net Debt 탭 연결 완료
- [x] 골든 회귀 테스트 (FDD-605, FDD-705) — test_nwc_golden.py(30) + test_debt_golden.py(30) = 60 골든
- [x] Alembic Migration — 002_add_nwc_and_debt_tables.py (4 테이블)

**산출물:** NWC 엔진 v1 ✅, Net Debt 엔진 v1 ✅, peg 시뮬레이터 ✅

---

### Sprint 6: 이상치 탐지 + AI Agent v1 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | ML 기반 이상치 스코어링 + LLM 에이전트 초기 통합 |
| EPIC | EPIC 5 (FDD-504), EPIC 12 (부분) |
| 상태 | **완료 (100%)** — 595 tests (누적) |

**완료 항목:**
- [x] 이상치 스코어링 5종 (Z-score 30%, Amount 25%, Timing 20%, Keyword 15%, Benford 10%) (FDD-504)
- [x] AnomalyEngine — `engines/anomaly_engine.py`, 순수함수 + Evidence 반환
- [x] Issue 모델 + API (`/api/v1/deals/{id}/issues`) — 15개 엔드포인트
- [x] QoE Analyzer Agent + CoA Mapper Agent 프롬프트 v1.0
- [x] LLM Guardrails 기본 구현 (금액 교차검증, JSON Schema 강제)
- [x] Structured Output JSON 스키마 정의
- [x] 골든 회귀 테스트 30개 시나리오 (test_anomaly_golden.py)

**산출물:** 이상치 탐지기 ✅, AI Agent v1 (QoE + CoA) ✅

---

## Phase 3: 보고서 자동생성 (Sprint 7~9)

### Sprint 7: Report Schema + PPT 생성 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | Report Schema IR 정의 + PPT Renderer v1 |
| EPIC | EPIC 8, EPIC 9 |
| MVP Story | FDD-801, FDD-802, FDD-901 |
| 상태 | **완료 (100%)** — 622 tests (누적) |

**완료 항목:**
- [x] Report Schema v1 정의 — 10 블록 타입 (cover/kpi/table/chart/text/claim/issue/methodology/scope/appendix) (FDD-801)
- [x] Block: TableBlock v1 + ChartBlock v1 + ClaimBlock v1 (FDD-802~804)
- [x] PPT Renderer v1 — 10 블록 렌더링, 표 오버플로우 페이지네이션 (FDD-901~902)
- [x] pptx-service `/render` 엔드포인트 구현
- [x] report_builder.py (376줄): engines → JSON IR
- [x] Report API 3개 엔드포인트 (generate, preview, ir)
- [x] Frontend: IssuePage + ReportPage 구현

**산출물:** Report Schema IR ✅, PPT 보고서 자동생성 v1 ✅

---

### Sprint 8: 품질 게이트 + 회귀 테스트 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | 보고서 품질 자동 검사 + 골든 파일 회귀 |
| EPIC | EPIC 16 |
| MVP Story | FDD-1602, FDD-1603, FDD-1604 |
| 상태 | **완료 (100%)** — 775 tests (누적, +153 QA) |

**완료 항목:**
- [x] 골든 데이터셋 14 케이스 구축 (FDD-1601)
- [x] 보고서 골든 테스트 — 표 수치 diff (FDD-1602)
- [x] Layout QA 자동검사 — placeholder 치환, 텍스트 오버플로우 (FDD-1603)
- [x] Evidence QA 자동검사 — 커버리지, 무결성 (FDD-1604)
- [x] 성능 회귀 — SLA 7개 체크 (GL 100만행 < 5분) (FDD-1605)
- [x] QA 모듈 4종: report_qa, layout_qa, evidence_qa, performance_qa

**산출물:** 자동 QA 파이프라인 ✅, 골든 데이터셋 ✅

---

### Sprint 9: Word 보고서 + 차트 서비스 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | DOCX 자동생성 + Chart Service |
| EPIC | EPIC 11, EPIC 13 |
| 상태 | **완료 (100%)** — 881 tests (누적, +106 new) |

**완료 항목:**
- [x] Word 렌더러 (python-docx) — 10 블록 타입, 500+ 줄 (FDD-1101~1103)
- [x] 차트 서비스 (Plotly) — line/bar/pie/waterfall, facade 패턴 (FDD-1301~1303)
- [x] Narrative Engine — 6 builtin 템플릿 + Jinja2 (QoE/NWC/Debt/exec) (FDD-1201~1202)
- [x] Chart API 3개 엔드포인트 (ebitda-bridge, nwc-bridge, debt-bridge)
- [x] Design System YAML 로더 + Big 4 스타일

**산출물:** Word 보고서 v1 ✅, Chart Service v1 ✅, Narrative Engine v1 ✅

---

## Phase 4: 고급 기능 (Sprint 10~11)

### Sprint 10: 템플릿 주입 + Delta Report — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | 고객 템플릿 유지 PPT + 정의 변경 영향 리포트 |
| EPIC | EPIC 10, EPIC 15 |
| 상태 | **완료 (100%)** — 993 tests (누적, +112 new) |

**완료 항목:**
- [x] Template Contract v1 + 슬롯 주입 (FDD-1001~1002)
- [x] PPT 템플릿 주입 v1 — Delta 주입 포함 (FDD-1003)
- [x] Delta 계산 엔진 — 정의 버전 간 비교 (FDD-1501)
- [x] Delta Report 자동 삽입 (FDD-1502)
- [x] 분쟁 민감 항목 자동 강조 — 5개 탐지 규칙 (FDD-1503)
- [x] Template API 21개 엔드포인트

**산출물:** 템플릿 주입 PPT v1 ✅, Delta Report v1 ✅

---

### Sprint 11: 보안/감사 + 운영 — COMPLETE (Phase 1~4 전체 완료)

| 구분 | 내용 |
|------|------|
| 목표 | RBAC + 감사로그 + 외부배포본 마스킹 + 운영 기반 |
| EPIC | EPIC 10, EPIC 14, EPIC 15, EPIC 17, EPIC 18 |
| 상태 | **완료 (100%)** — 143 Sprint 11 테스트, 전체 1,155 테스트 |

**완료 항목:**

- [x] RBAC v1 + JWT Auth (FDD-1701) — Phase 1: 4 Roles, 11 Permissions, JWT access/refresh, 41 tests
- [x] 감사로그 v2 강화 (FDD-1702) — Phase 2: before/after_state, changed_fields, expires_at, 26 tests
- [x] 데이터 보존/파기 정책 (FDD-1703) — Phase 2: 7 retention types, summary/purge/set-expiry API
- [x] Evidence Index 생성 (FDD-1401) — Phase 3: index_builder.py, structured evidence index
- [x] 외부배포본 모드 + 마스킹 (FDD-1402, FDD-1404) — Phase 3: 4 DistributionMode, mask engine, comparator, 31 tests
- [x] Report Generation Job 오케스트레이션 (FDD-1801) — Phase 4: 5 JobStatus, 5 JobType, orchestrator, 45 tests
- [x] Prometheus 메트릭 (FDD-1802) — Phase 4: 6 metrics (request/latency/active/error/engine/job)
- [x] Alembic Migration 003~004 — users table + sprint11 phase2-4 tables

**Phase별 산출물:**

| Phase | 범위 | 주요 산출물 | 테스트 |
|-------|------|-------------|--------|
| Phase 1 | RBAC + Auth | User 모델, JWT, Auth API 6ep, Frontend Auth | 41 |
| Phase 2 | Audit + Retention | AuditLog v2, RetentionPolicy 7종, Audit/Retention API | 26 |
| Phase 3 | Masking + Evidence | MaskingEngine, EvidenceIndex, 4 배포모드, Comparator | 31 |
| Phase 4 | Jobs + Observability | JobOrchestrator, Progress API, Prometheus 6 metrics | 45 |

**산출물:** 보안 레이어 ✅, 감사추적 ✅, 데이터 보존 ✅, 외부배포본 마스킹 ✅, 운영 파이프라인 ✅

---

## Phase 5: 안정화 + 출시 (Sprint 12)

### Sprint 12: 통합 테스트 + 베타 릴리즈 — COMPLETE (100%)

| 구분 | 내용 |
|------|------|
| 목표 | End-to-end 통합 테스트 + 베타 파일럿 |
| 상태 | **완료 (100%)** — 1,175 tests + E2E 39 scenarios |

**완료 항목:**
- [x] Playwright E2E 테스트 — 9 POMs, 10 specs, 39 시나리오 (`e2e/`)
- [x] Security 테스트 — 20 tests (FDD-1405 데이터 누출 + FDD-1705 권한 우회)
- [x] Chaos 테스트 — 10종 장애 주입 (FDD-1805)
- [x] 성능 벤치마크 스크립트 (`scripts/performance_benchmark.py`)
- [x] CI 워크플로 — `ci.yml` + `e2e.yml` (`.github/workflows/`)
- [x] 프로덕션 배포 자산 — `docker-compose.prod.yml`, `Dockerfile.prod` (BE/FE), `nginx.conf`
- [x] 배포 스크립트 — `scripts/deploy.sh` (up/down/restart/backup/health/create-admin)
- [x] 운영 문서 — deployment-guide, rollback-procedure, runbook, partner-onboarding

**산출물:** 베타 릴리즈 ✅, E2E 테스트 스위트 ✅, 프로덕션 배포 준비 ✅

---

## Phase 6: 프론트엔드 고도화 (Post-Sprint 12)

### 프론트엔드 AMIC 스타일 리디자인 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | AMIC 브랜드 디자인 시스템 적용 (Big 4 / IB 수준 전문 UI) |
| 상태 | **Phase 1~6 전체 완료** |

**완료 항목:**
- [x] Phase 1-2: 디자인 토큰 + Tailwind 확장 + 레이아웃 컴포넌트 (7개)
- [x] Phase 3: UI 컴포넌트 라이브러리 (15개: Button, Card, KpiCard, Modal, Input, Select, DataTable, Badge, Skeleton 등)
- [x] Phase 4: 11개 페이지 마이그레이션 (DealList, Workspace, Definition, Upload, Mapping, QoE, NWC, NetDebt, Issues, Report, Login)
- [x] Phase 5: Recharts 차트 컴포넌트 (6개: FinancialBarChart, TrendLineChart, WaterfallChart, ChartTooltip)
- [x] Phase 6: 모바일 반응형 + 접근성 강화 (WCAG 2.1 AA) — E2E 37개 테스트

**산출물:** 디자인 시스템 문서 2개, 컴포넌트 31개, 유틸리티 3개, E2E 접근성 테스트 2개

---

## Phase 7: Production Hardening + FDD 워크플로우 (Sprint 13+)

> 상세 계획: [sprint-13-integrated-plan.md](docs/plan/sprint-13-integrated-plan.md)

### Sprint 13: Production Hardening + FDD 워크플로우 프론트엔드 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | 프로덕션 안정화 + FDD 5단계 워크플로우 UI |
| 상태 | **완료 (100%)** — Track A 5/5, Track B 5/5 |

**Track A: Production Hardening (인프라/운영)**
- [x] Phase A1: 로컬 구동 검증 (Docker Compose + 전체 워크플로)
- [x] Phase A2: CI/CD 강화 (branch protection, PR template, CODEOWNERS, pytest-cov 80%)
- [x] Phase A3: 모니터링 & 관측성 (Prometheus + Grafana 대시보드 2개)
- [x] Phase A4: 성능 벤치마크 (SLA 실측, 7개 벤치마크)
- [x] Phase A5: Beta Pilot 준비 (SSL, 파트너 온보딩, 피드백 템플릿)

**Track B: FDD 워크플로우 프론트엔드 재설계**
- [x] Phase B1: 백엔드 모델 확장 (DealPhase 5단계, VdrFolder 7종, ReportVersion)
- [x] Phase B2: WorkflowStepper + Overview + Sidebar 재구성
- [x] Phase B3: Deal Setup Wizard (4스텝 멀티 위저드)
- [x] Phase B4: VDR (Virtual Data Room) 모델/API 6ep/UI
- [x] Phase B5: Report Version 관리 (DRAFT→FINAL, 버전 목록/생성/확정/다운로드)

**산출물:** Production Hardening ✅, FDD 5단계 워크플로우 ✅

---

### Sprint 14: 기술부채 해소 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | Multi-LLM 연동 + BaseAgent 리팩토링 + DB 의존 테스트 정리 |
| 상태 | **완료 (100%)** — 커밋 `7bab6ee` |

**완료 항목:**
- [x] Multi-LLM 클라이언트 (Anthropic + OpenAI + Gemini) — `app/services/llm/client.py`
- [x] BaseAgent 리팩토링 — provider 필드, 실제 LLM 호출 + 재시도 + fallback
- [x] 에이전트 업데이트 (coa_mapper, qoe_analyzer) — super().run() 활용
- [x] NWC multi-period — entry_date 기반 월별 잔액 자동 집계
- [x] 인제스트 구조화 로깅 추가
- [x] PostgreSQL/Docker 의존 테스트 정리 (Sprint 15에서 복원)

**산출물:** Multi-LLM 클라이언트 ✅, BaseAgent 리팩토링 ✅

---

### Sprint 15: Testcontainers 마이그레이션 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | SQLite/PostgreSQL 듀얼 모드 테스트 인프라 + 삭제 테스트 복원 |
| 상태 | **완료 (100%)** — 1,209 tests passed, 커밋 `02cf90d` |

**완료 항목:**
- [x] Phase 1: conftest.py 듀얼 모드 (SQLite 기본 + `--use-pg` PostgreSQL)
- [x] Phase 2: 삭제된 테스트 31개 파일 복원 (+9,948줄) + FK 호환성 수정
- [x] Phase 3: CI/CD `backend-pg` Job 추가 + pytest markers

**산출물:** Testcontainers 듀얼 모드 ✅, 1,209 tests ✅

---

### Sprint 16: Multi-Entity + Multi-Currency 연결 분석 — COMPLETE

| 구분 | 내용 |
|------|------|
| 목표 | 멀티 엔티티(TARGET/SUBSIDIARY/SPV) + 멀티 통화 FX 변환 + 연결 분석 |
| 상태 | **완료 (100%)** — 1,303 tests passed (+94 new) |

**완료 항목:**
- [x] Entity 모델 + CRUD API — 4 EntityType, parent-child, ownership_pct
- [x] ExchangeRate 모델 + CRUD API — 3 RateType, bulk 생성, 필터 조회
- [x] FX Service — get_rate, convert_amount, build_fx_converted_tb_map
- [x] Consolidation Engine (pure) — 엔티티 합산, IC 제거, 소수지분 계산
- [x] Consolidation Service — 멀티 엔티티 오케스트레이션 + FX 변환
- [x] Consolidation API — POST /run + GET /entities-summary
- [x] Period Extractor — 파일명/헤더에서 회계기간 자동 추출
- [x] Alembic Migration 006 — entity + exchange_rate 테이블
- [x] 테스트 94건 신규 (engine 16 + fx 13 + entity API 10 + exchange rate API 11 + consolidation service 8 + consolidation API 6 + period extractor 30)

**산출물:** 연결 분석 엔진 ✅, FX 서비스 ✅, Entity/ExchangeRate API ✅

---

## Sprint별 EPIC-Story 매핑 요약

| Sprint | Phase | EPIC | MVP Story 수 | 비고 |
|--------|-------|------|-------------|------|
| 1 | 기반 | 1 | - | **COMPLETE** |
| 2 | 기반 | 2 | 2 | **COMPLETE** — 데이터 파이프라인 |
| 3 | 기반 | 3, 4 | 5 | **COMPLETE** — 매핑 + Evidence |
| 4 | 분석 | 5 | 1 | **COMPLETE (100%)** — QoE 엔진 + Frontend |
| 5 | 분석 | 6, 7 | 3 | **COMPLETE (100%)** — NWC + Net Debt + Frontend |
| 6 | 분석 | 5(일부), 12(일부) | - | **COMPLETE** — 이상치 + AI Agent (595 tests) |
| 7 | 보고서 | 8, 9 | 3 | **COMPLETE** — IR + PPT (622 tests) |
| 8 | 보고서 | 16 | 3 | **COMPLETE** — 품질 게이트 (775 tests) |
| 9 | 보고서 | 11, 13 | - | **COMPLETE** — Word + Chart (881 tests) |
| 10 | 고급 | 10, 15 | - | **COMPLETE** — 템플릿 + Delta (993 tests) |
| 11 | 고급 | 10, 14, 15, 17, 18 | - | **COMPLETE** — 보안 + 운영 (1,155 tests) |
| 12 | 출시 | 전체 | - | **COMPLETE** — 통합 + 베타 (1,175 tests + E2E 39) |
| 13 | Hardening | 전체 | - | **COMPLETE** — Production Hardening + FDD Workflow |
| 14 | 기술부채 | - | - | **COMPLETE** — Multi-LLM + BaseAgent 리팩토링 |
| 15 | 테스트 인프라 | - | - | **COMPLETE** — Testcontainers 듀얼 모드 (1,209 tests) |
| 16 | 연결 분석 | - | - | **COMPLETE** — Multi-Entity + Multi-Currency (1,303 tests) |

---

## 마일스톤

| 마일스톤 | Sprint | 산출물 | 상태 |
|----------|--------|--------|------|
| **M1: 데이터 파이프라인** | 3 완료 | 업로드→매핑→재구성 가능 | **ACHIEVED** ✅ |
| **M2: 분석 엔진 MVP** | 5 완료 | QoE/NWC/Net Debt 계산 가능 | **ACHIEVED** ✅ |
| **M3: PPT 보고서 v1** | 7 완료 | IR→PPT 자동 생성 가능 | **ACHIEVED** ✅ |
| **M4: 품질 게이트** | 8 완료 | 자동 QA 파이프라인 | **ACHIEVED** ✅ |
| **M5: Word 보고서** | 9 완료 | PPT + Word 양쪽 생성 | **ACHIEVED** ✅ |
| **M6: 베타 릴리즈** | 12 완료 | 베타 파일럿 배포 | **ACHIEVED** ✅ |
| **M7: Production Ready** | 15 완료 | Hardening + Multi-LLM + Testcontainers | **ACHIEVED** ✅ |
| **M8: Multi-Entity** | 16 완료 | 연결 분석 + FX + Entity/ExchangeRate | **ACHIEVED** ✅ |

---

## 리스크 및 의존성

| 리스크 | 영향 | 완화 전략 |
|--------|------|-----------|
| 대용량 GL 성능 | Sprint 2~8 | 스트리밍 인제스트 + 인덱싱 전략 |
| LLM 비용 폭주 | Sprint 6+ | 토큰 제한 + Rate Limit + 비용 모니터링 |
| 회계 정확성 오류 | 전체 | Decimal 강제 + tie-out 자동 검증 + 골든 테스트 |
| 고객 템플릿 다양성 | Sprint 10 | Template Contract 표준화 + 파일럿 3종 |
| ~~PostgreSQL↔SQLite 테스트 차이~~ | ~~Sprint 2+~~ | ~~✅ Sprint 15에서 testcontainers 듀얼 모드로 해결~~ |

---

*문서 끝*
