# Sprint 13: Production Hardening + FDD 워크플로우 프론트엔드 — 통합 계획

> 작성일: 2026년 02월 09일 15시 40분 49초
> 상태: PLANNED
> 통합 문서: sprint-13-production-hardening.md + sprint-13-fdd-workflow-frontend.md

---

## 1. 개요

Sprint 13은 두 가지 병렬 트랙으로 구성됩니다:

- **Track A — Production Hardening**: 로컬 구동 검증, CI/CD 강화, 모니터링, 성능 벤치마크, Beta Pilot
- **Track B — FDD 워크플로우 프론트엔드**: FDD 실무 5단계 워크플로우 기반 UI 재설계 + 백엔드 확장

```text
Track A (인프라/운영)                Track B (워크플로우 UI)
─────────────────────               ─────────────────────
A1: 로컬 구동 검증          ←─┐     B1: 백엔드 모델 확장
A2: CI/CD 강화                 │     B2: WorkflowStepper + Overview
A3: 모니터링 (Prometheus)      │     B3: Deal Setup Wizard + Sidebar
A4: 성능 벤치마크              │     B4: VDR 모델/API/UI
A5: Beta Pilot 준비       ────┘     B5: Report Version 관리
```

> A1 완료 후 Track A/B 병렬 진행 가능. A5는 B 트랙 완료 후 최종 검증.

---

## 2. Track A — Production Hardening

### Phase A1: 로컬 구동 검증

| 작업 | 설명 | 상태 |
|------|------|------|
| Docker Compose 구동 | `make up` → 4서비스 기동 확인 (db, backend, pptx, frontend) | PENDING |
| DB 마이그레이션 | `make migrate` → Alembic 4개 버전 적용 확인 | PENDING |
| 브라우저 접속 | http://localhost:5173 → 로그인/딜 목록 정상 표시 | PENDING |
| 전체 워크플로 테스트 | Deal 생성 → 업로드 → 매핑 → QoE/NWC/Debt → 리포트 생성 | PENDING |
| Node.js 설치 확인 | Node.js 20+ 로컬 설치 (E2E/lint 실행용) | PENDING |
| E2E 스모크 테스트 | `cd e2e && npm test` → Playwright 39 시나리오 통과 | PENDING |

### Phase A2: CI/CD 강화

| 작업 | 설명 | 상태 |
|------|------|------|
| GitHub 리포 설정 | branch protection (main: 1 approver + CI pass) | PENDING |
| PR 템플릿 | `.github/pull_request_template.md` 추가 | PENDING |
| CI 워크플로 검증 | `ci.yml` + `e2e.yml` → GitHub Actions 실행 확인 | PENDING |
| CODEOWNERS | `.github/CODEOWNERS` — auth/, engines/ 영역 설정 | PENDING |
| 테스트 커버리지 | pytest-cov 80% 목표 설정 + CI 게이트 추가 | PENDING |

### Phase A3: 모니터링 & 관측성

| 작업 | 설명 | 상태 |
|------|------|------|
| Prometheus | docker-compose에 prometheus 서비스 추가 | PENDING |
| Grafana | docker-compose에 grafana 서비스 추가 | PENDING |
| 대시보드 | API 지연시간, 에러율, 엔진 처리 시간, 잡 성공률 | PENDING |
| 로그 수집 | Loki 또는 파일 기반 JSON 로그 수집 | PENDING |
| 알림 설정 | 에러율 > 1%, 지연 > 5s 시 알림 | PENDING |

### Phase A4: 성능 벤치마크

| 작업 | SLA 목표 | 상태 |
|------|----------|------|
| GL 인제스트 (100만 행) | < 5분 | PENDING |
| QoE 계산 | < 30초 | PENDING |
| PPT 렌더링 | < 2분 | PENDING |
| Word 렌더링 | < 1분 | PENDING |
| API 응답 (95th pctl) | < 500ms | PENDING |
| DB Slow Query 프로파일링 | 인덱스 최적화 | PENDING |
| FE 번들 사이즈 | < 500KB initial | PENDING |

### Phase A5: Beta Pilot 준비

| 작업 | 설명 | 상태 |
|------|------|------|
| 스테이징 배포 | `docker-compose.prod.yml` + `scripts/deploy.sh up` | PENDING |
| 시크릿 설정 | `.env.production` — JWT_SECRET, DB 비밀번호, CORS | PENDING |
| SSL/TLS | 리버스 프록시 HTTPS 설정 (Nginx + certbot) | PENDING |
| 파트너 선정 | 2~3곳 파일럿 파트너 선정 | PENDING |
| 온보딩 실행 | `docs/operations/partner-onboarding.md` 체크리스트 | PENDING |
| 피드백 수집 | 사용자 피드백 폼 + 이슈 트래커 연동 | PENDING |

---

## 3. Track B — FDD 워크플로우 프론트엔드 재설계

### 3.1 FDD 워크플로우 5단계

```text
[1. MoU 체결] → [2. VDR 개설] → [3. 자료 업로드] → [4. 자료 검토] → [5. 보고서 작성]
     │              │               │                │               │
   Deal 생성    폴더 구조 설정   파일 업로드      분석 수행       보고서 생성
```

| 단계 | 설명 | 완료 조건 |
|------|------|-----------|
| 1. MoU 체결 | 클라이언트/타겟 정보, 팀 구성, FDD 범위 설정 | 필수 정보 입력 완료 |
| 2. VDR 개설 | Virtual Data Room 폴더 구조 생성 | 기본 폴더 구조 생성 |
| 3. 자료 업로드 | 재무 자료(TB, GL 등) 업로드 | 필수 파일(TB/GL) 업로드 완료 |
| 4. 자료 검토 | 계정 매핑, QoE/NWC/Debt 분석, 이상치 탐지 | Definition 승인 완료 |
| 5. 보고서 작성 | 최종 FDD 보고서 생성 | 보고서 Final 확정 |

### 3.2 설계 원칙

- **VDR**: 폴더 구조 + 업로드 기능만 (접근 권한 관리 제외)
- **보고서**: 단순 버전 관리 (Draft/Final 상태만)
- **기존 활용**: 분석 페이지(QoE/NWC/Debt 등) 최대한 재사용

### Phase B1: 백엔드 모델 확장

#### Deal 모델 확장

```python
class DealPhase(str, enum.Enum):
    MOU = "MOU"                    # Phase 1: MoU 체결
    VDR_SETUP = "VDR_SETUP"        # Phase 2: VDR 개설
    DATA_UPLOAD = "DATA_UPLOAD"    # Phase 3: 자료 업로드
    ANALYSIS = "ANALYSIS"          # Phase 4: 자료 검토
    REPORTING = "REPORTING"        # Phase 5: 보고서 작성

class Deal(Base):
    # 기존 필드 유지
    # 신규: 클라이언트/타겟 정보, 팀 구성, FDD 범위, 워크플로우 상태
    client_name, client_contact_email, target_company_name
    team_partner_id, team_manager_id
    scope_qoe, scope_nwc, scope_debt
    current_phase: DealPhase
```

#### VDR 모델 (신규)

```python
class VdrFolderType(str, enum.Enum):
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"
    ACCOUNTS_RECEIVABLE = "ACCOUNTS_RECEIVABLE"
    ACCOUNTS_PAYABLE = "ACCOUNTS_PAYABLE"
    BANK_DEBT = "BANK_DEBT"
    LEASE = "LEASE"
    OTHERS = "OTHERS"
    CUSTOM = "CUSTOM"

class VdrFolder(Base):
    __tablename__ = "vdr_folder"
    # id, deal_id, parent_id, name, folder_type, order_index, is_required, created_at
```

#### ReportVersion 모델 (신규)

```python
class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"

class ReportVersion(Base):
    __tablename__ = "report_version"
    # id, deal_id, version, status, file_path, file_format, options, created_by, created_at
```

#### UploadFile 확장

```python
# vdr_folder_id FK 추가 → VDR 폴더 연결
```

#### Alembic 마이그레이션

```bash
alembic revision --autogenerate -m "add_workflow_vdr_report_version"
```

### Phase B2: 워크플로우 UI + 사이드바

#### 신규 컴포넌트

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| WorkflowStepper | `components/workflow/WorkflowStepper.tsx` | 5단계 진행 상태 시각화 |
| StepIndicator | `components/workflow/StepIndicator.tsx` | 개별 스텝 상태 표시 |
| StepContent | `components/workflow/StepContent.tsx` | 스텝별 상세 내용 + 액션 |

#### 사이드바 재구성

```text
[Current Deal: {deal_name}]

  ─── Workflow ───
  • Overview (스텝퍼 대시보드)

  ─── Phase 1: Setup ───
  • Deal Setup (MoU 정보)
  • VDR (Data Room)

  ─── Phase 2: Analysis ───
  • Definitions
  • Mapping
  • QoE Analysis
  • NWC Analysis
  • Net Debt
  • Issues

  ─── Phase 3: Report ───
  • Report Generator
```

### Phase B3: Deal Setup Wizard

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| DealSetupWizard | `components/deal/DealSetupWizard.tsx` | 멀티스텝 딜 생성 마법사 |
| TeamSelector | `components/deal/TeamSelector.tsx` | 팀원(Partner/Manager) 선택 |
| ScopeSelector | `components/deal/ScopeSelector.tsx` | FDD 범위(QoE/NWC/Debt) 선택 |

### Phase B4: VDR (Virtual Data Room)

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| VdrFolderTree | `components/vdr/VdrFolderTree.tsx` | 폴더 트리 뷰 |
| VdrFolder | `components/vdr/VdrFolder.tsx` | 개별 폴더 컴포넌트 |
| VdrUploadZone | `components/vdr/VdrUploadZone.tsx` | 폴더별 드래그앤드롭 업로드 |
| VdrFileList | `components/vdr/VdrFileList.tsx` | 폴더 내 파일 목록 |

#### VDR API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/deals/{deal_id}/vdr/init` | 기본 폴더 구조 초기화 |
| GET | `/api/v1/deals/{deal_id}/vdr/folders` | 폴더 목록 조회 (트리) |
| POST | `/api/v1/deals/{deal_id}/vdr/folders` | 폴더 생성 |
| PUT | `/api/v1/deals/{deal_id}/vdr/folders/{folder_id}` | 폴더 수정 |
| DELETE | `/api/v1/deals/{deal_id}/vdr/folders/{folder_id}` | 폴더 삭제 |
| GET | `/api/v1/deals/{deal_id}/vdr/folders/{folder_id}/files` | 폴더별 파일 목록 |

### Phase B5: Report Version 관리

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| ReportVersionList | `components/report/ReportVersionList.tsx` | 보고서 버전 목록 |
| ReportVersionCard | `components/report/ReportVersionCard.tsx` | 버전별 카드 (상태, 다운로드) |

#### Report Version API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/deals/{deal_id}/reports/versions` | 버전 목록 조회 |
| POST | `/api/v1/deals/{deal_id}/reports/versions` | 새 버전 생성 |
| PUT | `/api/v1/deals/{deal_id}/reports/versions/{version}/finalize` | Final 확정 |
| GET | `/api/v1/deals/{deal_id}/reports/versions/{version}/download` | 다운로드 |

#### Workflow API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/deals/{deal_id}/workflow` | 워크플로우 진행 상태 조회 |
| PUT | `/api/v1/deals/{deal_id}/workflow/phase` | 현재 단계 업데이트 |

---

## 4. 라우팅 변경

### 전체 라우트 구조

```text
/login                        → LoginPage
/deals                        → DealListPage
/deals/new                    → DealSetupWizardPage (신규)
/deals/:dealId                → DealWorkspacePage
  ├── /                       → WorkflowOverviewPage (변경)
  ├── /setup                  → DealSetupPage (신규)
  ├── /vdr                    → VdrPage (신규)
  ├── /definitions            → DefinitionPage (기존)
  ├── /mapping                → MappingPage (기존)
  ├── /qoe                    → QoEPage (기존)
  ├── /nwc                    → NWCPage (기존)
  ├── /netdebt                → NetDebtPage (기존)
  ├── /issues                 → IssuesPage (기존)
  └── /report                 → ReportPage (버전 관리 추가)
```

---

## 5. 구현 순서 및 일정

### Track A 순서 (순차)

| 순서 | Phase | 작업 | 예상 |
|------|-------|------|------|
| 1 | A1 | 로컬 구동 검증 | 1일 |
| 2 | A2 | CI/CD 강화 | 0.5일 |
| 3 | A3 | 모니터링 스택 | 1일 |
| 4 | A4 | 성능 벤치마크 | 1일 |
| 5 | A5 | Beta Pilot (B 트랙 후) | 1일 |

### Track B 순서 (A1 완료 후 병렬)

| 순서 | Phase | 작업 | 예상 |
|------|-------|------|------|
| 1 | B1 | 백엔드 모델 확장 + 마이그레이션 | 0.5일 |
| 2 | B2 | WorkflowStepper + Overview + Sidebar | 1일 |
| 3 | B3 | Deal Setup Wizard | 1일 |
| 4 | B4 | VDR 모델/API/UI | 1.5일 |
| 5 | B5 | Report Version 관리 | 0.5일 |

**총 예상: Track A 4.5일 + Track B 4.5일 = 병렬 진행 시 약 5~6일**

---

## 6. 수정할 주요 파일

### 프론트엔드

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/App.tsx` | 신규 라우트 추가 (/deals/new, /setup, /vdr) |
| `frontend/src/components/layout/Sidebar.tsx` | 섹션 그룹화, VDR 메뉴 추가 |
| `frontend/src/pages/DealWorkspacePage.tsx` | Overview → WorkflowOverviewPage |
| `frontend/src/pages/DealListPage.tsx` | New Deal 클릭 시 /deals/new 이동 |
| `frontend/src/pages/ReportPage.tsx` | 버전 관리 UI 추가 |

### 백엔드

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/models/deal.py` | DealPhase enum, 워크플로우 필드 추가 |
| `backend/app/models/vdr.py` | VdrFolder 모델 (신규) |
| `backend/app/models/report.py` | ReportVersion 모델 (신규) |
| `backend/app/models/upload.py` | vdr_folder_id FK 추가 |
| `backend/app/schemas/deal.py` | 스키마 확장 |
| `backend/app/schemas/vdr.py` | VDR 스키마 (신규) |
| `backend/app/schemas/report.py` | ReportVersion 스키마 추가 |
| `backend/app/api/vdr.py` | VDR API (신규) |
| `backend/app/api/workflow.py` | Workflow API (신규) |
| `backend/app/api/reports.py` | 버전 관리 API 추가 |
| `backend/app/main.py` | 라우터 등록 |

### 인프라

| 파일 | 변경 내용 |
|------|-----------|
| `docker-compose.yml` | Prometheus + Grafana 서비스 (또는 별도 yml) |
| `.github/pull_request_template.md` | PR 템플릿 (신규) |
| `.github/CODEOWNERS` | 코드 소유자 (신규) |
| `config/grafana/dashboards/` | Grafana 대시보드 (신규) |

---

## 7. 검증 방법

### 단위 테스트

```bash
# 백엔드
cd backend && python -m pytest tests/vdr/ tests/workflow/ -v

# 프론트엔드
cd frontend && npm run lint && npx tsc --noEmit
```

### E2E 테스트 시나리오 (신규)

1. 딜 생성 플로우: /deals → New Deal → 4스텝 위저드 완료
2. VDR 플로우: VDR 초기화 → 폴더 생성 → 파일 업로드
3. 워크플로우 진행: 5단계 순차 진행 확인
4. 보고서 버전: Draft 생성 → Final 확정

### 성능 검증

| 항목 | 스크립트 | SLA |
|------|----------|-----|
| GL 인제스트 | `scripts/performance_benchmark.py` | < 5분 |
| API 응답 | 벤치마크 | < 500ms (p95) |
| FE 번들 | `npm run build` 후 확인 | < 500KB |

---

## 8. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Docker Desktop 미설치 | Phase A1 차단 | WSL2 + Docker Desktop 설치 가이드 |
| Node.js 미설치 | E2E/lint 불가 | Node.js 20 LTS 로컬 설치 |
| 스테이징 서버 부재 | Phase A5 지연 | 로컬 prod 모드로 대체 검증 |
| 성능 SLA 미달 | 파일럿 품질 | DB 인덱스 + 쿼리 최적화 |
| VDR 폴더 구조 복잡도 | 개발 지연 | 기본 6개 폴더만 지원, 커스텀 후순위 |
| 기존 UploadPage 호환성 | 기능 손상 | VDR 통합 선택적, 기존 업로드 유지 |
| 워크플로우 상태 동기화 | 상태 불일치 | 백엔드 자동 계산, FE는 표시만 |

---

## 9. 산출물

| 산출물 | 위치 |
|--------|------|
| Prometheus + Grafana 설정 | `docker-compose.monitoring.yml` |
| Grafana 대시보드 | `config/grafana/dashboards/` |
| PR 템플릿 | `.github/pull_request_template.md` |
| CODEOWNERS | `.github/CODEOWNERS` |
| 성능 벤치마크 결과 | `docs/benchmarks/` |
| WorkflowStepper 컴포넌트 | `frontend/src/components/workflow/` |
| VDR 컴포넌트 | `frontend/src/components/vdr/` |
| Deal Setup 컴포넌트 | `frontend/src/components/deal/` |
| Report Version 컴포넌트 | `frontend/src/components/report/` |
| VDR 모델/API | `backend/app/models/vdr.py`, `backend/app/api/vdr.py` |
| Workflow API | `backend/app/api/workflow.py` |
| Alembic 마이그레이션 | `backend/alembic/versions/005_*` |

---

## 10. 참고 문서

- 원본 계획 (Production Hardening): `docs/plan/sprint-13-production-hardening.md`
- 원본 계획 (FDD Workflow): `docs/plan/sprint-13-fdd-workflow-frontend.md`
- 현재 프론트엔드 구조: `docs/design/frontend-redesign-amic-style.md`
- Sprint 12 완료 현황: `FDD_프로젝트_진행현황.md`
- Deal 모델 정의: `backend/app/models/deal.py`
- 기존 라우팅: `frontend/src/App.tsx`

---

*문서 끝*
