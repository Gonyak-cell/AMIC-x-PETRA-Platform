# Sprint 13 Track A 완료 계획 — 93% → 100%

> 작성일: 2026년 02월 09일 22시 16분 54초
> 상태: EXECUTED (2026-02-10)
> 대상: Sprint 13 Track A 미완료 3건 (A1, A2 일부, A5 일부) → 전체 완료

---

## 1. 배경 (Context)

Sprint 13은 Track A(Production Hardening)와 Track B(FDD Workflow Frontend)로 구성.
Track B는 5/5 Phase 100% 완료. Track A는 A3(모니터링), A4(벤치마크)만 완료(3/5 = 60%).
나머지 A1, A2 일부, A5 일부를 완료하여 전체 프로젝트 진행률을 **93% → 100%**로 달성한다.

**미완료 항목:**

| 항목 | 상태 | 미완료 내역 |
|------|------|------------|
| A1: 로컬 구동 검증 | PENDING | Docker 환경 실행 + 전체 워크플로 수동 검증 (6개 항목) |
| A2: CI/CD 강화 | PARTIAL | Branch Protection ❌, Test Coverage Gate ❌ (CODEOWNERS ✅, PR 템플릿 ✅) |
| A5: Beta Pilot 준비 | PARTIAL | 파트너 선정 ❌, 온보딩 ❌, 피드백 수집 체계 ❌ (인프라 파일 전부 ✅) |

---

## 2. 실행 계획

### Step 1: CI Coverage Gate 추가 (A2 — 코드 변경)

**수정 파일:** `.github/workflows/ci.yml`

현재 pytest 실행 (coverage 미적용):
```yaml
- name: Pytest
  run: pytest --tb=short -q
```

변경 후:
```yaml
- name: Pytest with Coverage
  run: pytest --cov=app --cov-report=term --cov-report=xml --cov-fail-under=80 --tb=short
```

- `pytest-cov>=6.0.0`은 이미 `backend/pyproject.toml`에 설치됨
- 80% 미달 시 CI 실패 → PR 머지 차단
- XML 리포트 생성으로 향후 Codecov 연동 가능

**로컬 검증:**
```bash
cd backend && pytest --cov=app --cov-report=term --cov-fail-under=80
```

---

### Step 2: GitHub Branch Protection 설정 (A2 — GitHub 설정)

`gh` CLI 또는 GitHub Web UI에서 `main` 브랜치 보호 활성화:

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["backend", "frontend", "pptx-service"]
  },
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "enforce_admins": false,
  "restrictions": null
}
EOF
```

**설정 요약:**
- PR 필수 (1 approver + stale review 자동 dismiss)
- CI 3개 잡(backend, frontend, pptx-service) 통과 필수
- Admin 바이패스 허용 (긴급 hotfix용)

**검증:**
```bash
gh api repos/{owner}/{repo}/branches/main/protection | jq .
```

---

### Step 3: Beta Pilot 피드백 수집 체계 구축 (A5 — 신규 파일 3건)

#### 3a. GitHub Issue Template — 베타 피드백

**파일:** `.github/ISSUE_TEMPLATE/beta-feedback.yml`

구조화된 피드백 수집 양식:
- 파트너사명, 딜 ID/이름
- 워크플로우 완료 여부 (드롭다운)
- 사용성 평가 (7개 항목 × 1~5점: 전체 편의성, 업로드/인제스트, 자동 매핑, QoE, NWC/Debt, 보고서 품질, 응답 속도)
- 발견된 문제점 (P0~P3 우선순위)
- 개선 제안 + 종합 의견
- 평균 딜 처리 시간

#### 3b. GitHub Issue Template — 베타 버그 리포트

**파일:** `.github/ISSUE_TEMPLATE/beta-bug-report.yml`

버그 리포트 양식:
- 심각도 드롭다운 (P0 Critical ~ P3 Cosmetic)
- 버그 설명, 재현 절차 (단계별)
- 예상 동작 vs 실제 동작
- 환경 정보 (브라우저/OS)
- 에러 로그 (코드 블록)

#### 3c. 파트너 선정 템플릿

**파일:** `docs/operations/partner-selection-template.md`

- 선정 기준 가중치 (FDD 경험 30%, 기술 역량 20%, 협업 의지 25%, 데이터 준비 15%, 규모 10%)
- 후보 리스트 테이블 (점수 기반 평가)
- 1차 컨택 이메일 템플릿
- 제안서 체크리스트
- 최종 선정 + 대기 파트너 기록란

---

### Step 4: 로컬 구동 검증 (A1 — 운영 검증)

6개 검증 항목을 순차 실행하고 결과를 보고서로 기록.

#### 4a. Docker Compose 구동 + DB 마이그레이션

```bash
make up          # 4서비스 기동 (db:5433, backend:8000, pptx:3100, frontend:5173)
make migrate     # Alembic 4버전 적용 (001_initial → 005_workflow_vdr_rv)
docker compose ps  # 전체 서비스 상태 확인
```

**성공 기준:** 4서비스 모두 running/healthy, `alembic current` → head

#### 4b. 브라우저 접속 확인

- http://localhost:5173 → 로그인 페이지 표시
- F12 콘솔 에러 0건

#### 4c. 전체 워크플로 수동 테스트 (8단계)

| 단계 | 작업 | 예상 결과 |
|------|------|-----------|
| 1 | Admin 계정 생성 | 계정 생성 성공 |
| 2 | 로그인 | 딜 리스트 페이지 표시 |
| 3 | 딜 생성 (DealSetupWizard) | 딜 상세 페이지 + WorkflowStepper |
| 4 | TB/GL 업로드 → 인제스트 | 업로드 성공 (< 5초) |
| 5 | 계정 매핑 → Tie-out | 매핑 완료 + Tie-out 통과 |
| 6 | QoE 분석 실행 | Adjusted EBITDA 결과 표시 |
| 7 | NWC/Net Debt 분석 실행 | 분류 결과 + 계산 결과 표시 |
| 8 | PPT 보고서 생성 → 다운로드 | .pptx 파일 다운로드 성공 |

#### 4d. E2E 스모크 테스트

```bash
cd e2e && npm install && npm test  # Playwright 39 시나리오
```

**성공 기준:** 전체 통과 (minor accessibility warnings 허용)

#### 4e. 검증 보고서 작성

**신규 파일:** `docs/operations/local-verification-report.md`
- 6개 항목별 PASS/FAIL 기록
- 발견된 이슈 → GitHub Issue 등록

---

### Step 5: 진행현황 문서 업데이트 (최종)

**파일:** `FDD_프로젝트_진행현황.md`

| 변경 위치 | 변경 전 | 변경 후 |
|-----------|---------|---------|
| 전체 진행률 바 | `93%` | `100%` |
| Sprint 진행률 | `12/13 (92%)` | `13/13 (100%)` |
| Track A 진행률 | `3/5 (60%)` | `5/5 (100%)` |
| Sprint 13 상태 | `IN PROGRESS` | `COMPLETE` |
| A1/A2/A5 상태 | PENDING/PARTIAL | DONE |
| 변경 이력 | — | Sprint 13 완료 엔트리 추가 |

---

## 3. 실행 순서 및 병렬화

```text
Step 1 (CI Coverage Gate)  ──┐
Step 2 (Branch Protection)   ├── 병렬 실행 (독립 작업)
Step 3a,3b,3c (Templates)  ──┘

Step 4a (Docker + Migrate) ──→ Step 4b (Browser)
                              ──→ Step 4c (Workflow Test) ──┐
                              ──→ Step 4d (E2E Test)       ──┤→ Step 4e (Report)
                                                             │
Step 5 (문서 업데이트) ←─────────────────────────────────────┘
```

- **Step 1, 2, 3**: 코드/설정/문서 변경 — 서로 독립적이므로 **병렬 실행**
- **Step 4**: 운영 검증 — Docker 기동 후 순차 (브라우저 → 워크플로/E2E → 보고서)
- **Step 5**: 문서 갱신 — 모든 작업 완료 확인 후 최종 실행

---

## 4. 산출물 요약

| 유형 | 파일 | 설명 |
|------|------|------|
| **수정** | `.github/workflows/ci.yml` | pytest-cov 80% gate 추가 |
| **신규** | `.github/ISSUE_TEMPLATE/beta-feedback.yml` | 베타 피드백 수집 양식 |
| **신규** | `.github/ISSUE_TEMPLATE/beta-bug-report.yml` | 베타 버그 리포트 양식 |
| **신규** | `docs/operations/partner-selection-template.md` | 파트너 선정 체계 |
| **신규** | `docs/operations/local-verification-report.md` | A1 검증 보고서 |
| **수정** | `FDD_프로젝트_진행현황.md` | 진행률 93% → 100% |

---

## 5. 검증 방법

| 항목 | 검증 명령/방법 | 성공 기준 |
|------|---------------|-----------|
| Coverage Gate | `cd backend && pytest --cov=app --cov-fail-under=80` | 80% 이상 + CI 통과 |
| Branch Protection | `gh api .../branches/main/protection` | 1 approver + CI 필수 |
| Issue Templates | GitHub UI → New Issue | 2개 템플릿 선택 가능 |
| Docker 구동 | `docker compose ps` | 4서비스 healthy |
| DB 마이그레이션 | `alembic current` | head (005번) |
| 전체 워크플로 | 수동 8단계 테스트 | Deal→Report 성공 |
| E2E | `cd e2e && npm test` | 39 시나리오 통과 |

---

## 6. 리스크 대응

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| Coverage 80% 미달 | 중 | 높음 | 로컬 측정 후 임시 임계값 하향(75%) 또는 테스트 추가 |
| A1 검증 시 워크플로 버그 발견 | 중 | 높음 | hotfix 브랜치 즉시 생성, +2일 버퍼 |
| E2E Windows 환경 문제 | 낮음 | 중 | 이미 39 시나리오 구현 확인됨 |
| 파트너 미확보 | 낮음 | 중 | 후보 풀 확대 (10곳+), 인센티브 제공 |

---

## 7. 완료 후 액션

1. **릴리즈 태그**: `git tag -a v0.13.0 -m "Sprint 13: Production Hardening + FDD Workflow"`
2. **Sprint 14 계획**: 베타 피드백 기반 P0~P1 이슈 + 기술 부채(LLM API 연동, SQLite→PostgreSQL 테스트)
3. **프론트엔드 통합**: `docs/plan/frontend-integration-plan.md` (KIIS + IM Module) — Sprint 14+ 별도 진행

---

*문서 끝*
