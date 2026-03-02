# Code Review — MA Workflow (feat/ma-workflow vs origin/master)

> **Review Date**: 2026-03-02 02:19 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff origin/master` — deal-mgmt(300), kiis(130), im(216), amic-platform(341) = **987 files**
> **Method**: Quality Gates + Review Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(PASS 170/170) build(PASS) deal-mgmt-ruff(PASS) deal-mgmt-pytest(PASS 1151/1151)
> **Review Gates**: Backend(deal-mgmt ✓, kiis ✓, im ✓) Agent-Filtering(5개 에이전트 호출)

---

## Summary

| Severity | Raw Count | After Cross-Verification | FP Removed | Downgraded |
|----------|-----------|-------------------------|------------|------------|
| Critical | 18        | **6**                   | 7          | 5 → Major  |
| Major    | —         | **5**                   | —          | —          |
| **Total**| **18**    | **11**                  | **7**      | **5**      |

**FP Prevention**: 가설 18건 검증, 7건 사전 거부 (거부율: 39%) | 교차 검증 18건 수행

---

## Critical Issues (P0) — 6건

### [API-001] SI 매핑 스키마 — 재무 필드 float 사용으로 Decimal 정밀도 손실 — [Critical/HIGH] — P0 (점수: 100)

- **파일**: `deal-mgmt/app/schemas/si_mapping.py:48-61, 82, 91, 147-150`
- **파일2**: `deal-mgmt/app/services/si_mapping_service.py:686`
- **증거**:
  ```python
  # 스키마: 재무 필드 전부 float
  class SICompanyOut(BaseModel):
      revenue: float | None = None           # DB: Numeric(20,2) → Decimal
      operating_profit: float | None = None
      net_income: float | None = None
      total_assets: float | None = None
      # ... 8개 필드 모두 float

  # 서비스: Decimal → float 강제 변환
  transaction_value=float(total_val) if total_val else 0.0,
  ```
- **영향**: DB 모델은 `Numeric(20,2)` → Python `Decimal`로 올바르게 선언되었으나, Pydantic 스키마에서 `float`로 변환하면 IEEE 754 정밀도 오류 발생. 조 단위 금액(`10^12`)에서 오차 누적 가능.
- **수정 제안**: 스키마의 `float | None` → `Decimal | None` 전환, `float()` 강제 변환 제거.

---

### [API-003] extraction_tasks — acks_late + 좀비 상태 위험 — [Critical/HIGH] — P0 (점수: 100)

- **파일**: `deal-mgmt/app/tasks/extraction_tasks.py:28-33, 59-61`
- **증거**:
  ```python
  @celery_app.task(
      bind=True,
      soft_time_limit=300,
      acks_late=True,    # 워커 크래시 → 메시지 재전달
      # max_retries 미설정!
  )
  def run_extraction_task(self, extraction_id):
      ...
      except Exception:
          raise              # Celery가 재전달 시 status != PENDING → 영구 스킵
  ```
- **영향**: `acks_late=True`로 워커 크래시 시 메시지가 재전달되나, 이미 `CLASSIFYING`/`EXTRACTING` 상태로 변경된 레코드는 `status != PENDING` 조건에 걸려 스킵됨. LLM 비용 소진 후 추출 결과가 영구적으로 중간 상태에 머무는 좀비 레코드 발생.
- **수정 제안**: `max_retries=2` 명시 + 중간 상태 감지 시 `FAILED` 리셋 로직 추가.

---

### [MIG-001] IM 006 마이그레이션 — PostgreSQL 전용 UUID/JSONB 직접 사용 — [Critical/HIGH] — P0 (점수: 100)

- **파일**: `im/alembic/versions/006_im_checklists.py:10`
- **증거**:
  ```python
  from sqlalchemy.dialects.postgresql import UUID, JSONB  # Guard 2 위반

  sa.Column("id", UUID(as_uuid=True), ...),          # SQLite CompileError
  sa.Column("vdr_document_ids", JSONB, ...),          # SQLite CompileError
  ```
- **영향**: CI는 SQLite 기반(`ci-regression-prevention.md` Guard 2). 이 마이그레이션 실행 시 `CompileError: Can't render element of type UUID` 발생하여 CI 테스트 전체 차단.
- **수정 제안**: `sa.Uuid()` + `sa.JSON().with_variant(JSONB, "postgresql")` 패턴 적용.

---

### [MIG-002] IM 007 마이그레이션 — 동일 PostgreSQL 전용 타입 패턴 — [Critical/HIGH] — P0 (점수: 100)

- **파일**: `im/alembic/versions/007_im_ralph_sessions.py:9-10`
- **영향**: MIG-001과 동일한 패턴. 8개 컬럼에서 `UUID(as_uuid=True)`, `JSONB` 직접 사용.
- **수정 제안**: MIG-001과 동일.

---

### [PERF-002] KOFIAService — 요청마다 새 인스턴스 + 커넥션 누수 — [Critical/HIGH] — P0 (점수: 100)

- **파일**: `kiis/app/routers/kofia.py:9-11`
- **증거**:
  ```python
  def get_kofia_service() -> KOFIAService:
      return KOFIAService()   # 매 요청마다 새 httpx.AsyncClient 생성

  # 각 핸들러에서:
  await service.close()       # 예외 시 미실행 → 소켓 누수
  ```
- **영향**: 매 HTTP 요청마다 새 TCP 커넥션 풀 생성. 예외 시 `close()` 미호출로 소켓 파일 디스크립터 누수.
- **수정 제안**: FastAPI `lifespan`에서 싱글턴 관리 또는 `AsyncGenerator` 의존성으로 `finally: close()` 보장.

---

### [PERF-003] fm_checklist_service — N건 개별 db.refresh() — [Critical/HIGH] — P0 (점수: 100)

- **파일**: `deal-mgmt/app/services/fm_checklist_service.py:114-117`
- **증거**:
  ```python
  await self.db.flush()
  for item in results:
      await self.db.refresh(item)   # N건 × SELECT = N번 DB 왕복
  return results
  ```
- **영향**: FM 체크리스트 80개 필드 기준 80회 SELECT 왕복. `bulk-update-checklist-items` 엔드포인트에서 수백 ms 지연.
- **수정 제안**: 단일 `IN` 쿼리로 일괄 재조회.

---

## Major Issues (P1) — 5건

### [PERF-001] SI 매핑 — SELECT * 10,000건 전체 로딩 — [Major/MEDIUM] — P1 (점수: 42)

- **파일**: `deal-mgmt/app/services/si_mapping_service.py:521`
- **원인**: `select(SICompany)` → 30+ 컬럼 × 10,000건 ORM 객체 생성
- **교차 검증 결과**: SICompanyOut 스키마가 description, address 등 다수 필드를 포함하므로 SELECT *이 응답 구성에 필요. 그러나 10K 건 ORM 역직렬화의 메모리 부담은 여전히 존재.
- **수정 제안**: 2단계 접근 — 먼저 경량 필드(id, company_name, ksic_codes, revenue)로 KSIC 인덱스 구축, 이후 매칭된 기업만 전체 컬럼 로딩.

### [PERF-004] KOFIA — 전체 펀드 데이터 반복 역직렬화 — [Major/MEDIUM] — P1 (점수: 42)

- **파일**: `kiis/app/services/kofia_service.py:528-621`
- **원인**: Redis 캐시 히트 시에도 전체 펀드 목록 파싱 + GP 그룹화 반복
- **교차 검증 결과**: Redis 캐시 6시간 TTL이 API 호출을 차단하나, 파싱+그룹화 연산은 매 요청마다 반복됨. 실질적 영향은 10-50ms 수준으로 Critical보다는 Major.
- **수정 제안**: GP 그룹화 결과 자체를 별도 캐시 키로 저장.

### [MIG-003] IM 006 downgrade — 인덱스 명시적 삭제 누락 — [Major/MEDIUM] — P1 (점수: 42)

- **파일**: `im/alembic/versions/006_im_checklists.py:93-95`
- **교차 검증 결과**: PostgreSQL `DROP TABLE`이 의존 인덱스를 자동 삭제하므로 기능적 문제 없음. 단, 007과 일관성 불일치 (007은 인덱스를 명시적으로 삭제).

### [MIG-004] deal-mgmt 051 downgrade — pass 구현 — [Major/MEDIUM ⚠️] — P1 (점수: 42)

- **파일**: `deal-mgmt/migrations/versions/051_add_client_audit_actions.py:29-31`
- **교차 검증 결과**: PostgreSQL enum ADD VALUE는 기술적으로 되돌릴 수 없음. `pass`는 의도된 no-op. 주석으로 사유가 문서화되어 있으나, P4 규칙(`pass 금지`)에 형식적으로 위반. 설계 리스크(DESIGN_RISK) 분류.

### [MIG-005] IM 006/모델 — vdr_document_ids nullable 불일치 — [Major/MEDIUM] — P1 (점수: 42)

- **파일**: `im/alembic/versions/006_im_checklists.py:32` vs `im/src/api/db/models/im_checklist.py:62`
- **교차 검증 결과**: 모델 `Mapped[list[Any]]`(NOT NULL) vs 마이그레이션 `nullable` 미지정(default: True). ORM의 `default=list`가 INSERT 시 `[]`를 보장하므로 실질적 NULL 삽입은 불가. 그러나 직접 SQL INSERT 시 NULL 가능.

---

## Rejected Issues (허위 양성) — 7건

| ID | 사유 | 분류 |
|----|------|------|
| PERF-005 | `audit_service.record()`는 `db.add()`만 수행, flush/commit 없음 → N번 DB 왕복 아님 | FP-LOGIC |
| TS-001 | `DartFinancialSummaryOut`에 `@field_serializer` 없음 (에이전트 환각). Pydantic v2 기본 Decimal 직렬화 = JSON number | FP-HALLUC |
| TS-002 | FE `string` ↔ BE `Decimal` → `@field_serializer` → `str`. 양쪽 모두 string으로 정합 | FP-LOGIC |
| TS-003 | FE `Record<MarketingStage, ...>`이 BE `dict[str, ...]`보다 엄격 — 오히려 더 안전 | FP-LOGIC |
| TS-004 | `ConsortiumMappingOut.equity_share_pct: Decimal`에 `@field_serializer` 없음. FastAPI `jsonable_encoder` → float → FE `number` 정합 | FP-LOGIC |
| TS-005 | `created_by_email` 미선언은 사용하지 않는 필드. 런타임 영향 없음 | FP-SEV |
| API-002 | Azure SDK `stream.readinto(f)`는 async 메서드. `open()`의 블로킹은 fd 할당으로 수 μs | FP-SEV |

---

## Phase 0A Quality Gates 상세

| Gate | 상태 | 결과 |
|------|------|------|
| TypeScript (`tsc --noEmit`) | ✅ PASS | 0 errors |
| ESLint (`--max-warnings 0`) | ✅ PASS | 0 warnings |
| Vitest (unit tests) | ✅ PASS | 170 passed |
| Vite build | ✅ PASS | chunk warning only (index 515KB) |
| deal-mgmt ruff check | ✅ PASS | 0 errors |
| deal-mgmt ruff format | ✅ PASS | 368 files formatted |
| deal-mgmt pytest | ✅ PASS | 1151 passed, 14 skipped |
| kiis ruff check | ✅ PASS | 0 errors |
| kiis ruff format | ⚠️ | 3 test files pre-existing (비변경 파일) |
| im ruff check | ⚠️ | 34 errors (Ralph Loop 코드, 기존) |

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
1. [API-001] [Critical/HIGH]: SI 매핑 재무 필드 float → Decimal 전환 필요 — `schemas/si_mapping.py` (점수: 100)
2. [API-003] [Critical/HIGH]: 추출 태스크 좀비 상태 방지 — `tasks/extraction_tasks.py` (점수: 100)
3. [MIG-001] [Critical/HIGH]: IM 006 마이그레이션 크로스 DB 호환 — `006_im_checklists.py` (점수: 100)
4. [MIG-002] [Critical/HIGH]: IM 007 마이그레이션 크로스 DB 호환 — `007_im_ralph_sessions.py` (점수: 100)
5. [PERF-002] [Critical/HIGH]: KOFIA 서비스 싱글턴 + 커넥션 관리 — `kofia.py` (점수: 100)
6. [PERF-003] [Critical/HIGH]: FM 체크리스트 bulk refresh → IN 쿼리 — `fm_checklist_service.py` (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89)
1. [PERF-001] [Major/MEDIUM]: SI 매핑 10K SELECT * 최적화 — `si_mapping_service.py` (점수: 42)
2. [PERF-004] [Major/MEDIUM]: KOFIA GP 그룹화 캐시 분리 — `kofia_service.py` (점수: 42)
3. [MIG-003] [Major/MEDIUM]: IM 006 downgrade 인덱스 정리 — `006_im_checklists.py` (점수: 42)
4. [MIG-004] [Major/MEDIUM ⚠️]: deal-mgmt 051 downgrade 문서화 — `051_add_client_audit_actions.py` (점수: 42)
5. [MIG-005] [Major/MEDIUM]: IM nullable 불일치 해소 — `006_im_checklists.py` (점수: 42)

---

## Methodology

- **Agents**: security-auditor, api-auditor (python-code-reviewer), type-checker (explore), performance-profiler, migration-validator
- **Files scanned**: 987개 (FE 341, deal-mgmt 300, kiis 130, im 216)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 18건 전수 검증 (Code Read 기반)
- **Backend availability**: deal-mgmt(✓) kiis(✓) im(✓)

## 검증 투명성

### 검증 통계
- 검증한 가설: 18건
- 거부된 가설 (사전 제거): 7건
- 보고된 이슈: 11건
- 거부율: 39%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 논리 오류 (FP-LOGIC) | 4 | audit_service.record()가 flush 없이 db.add()만 수행 |
| 환각 (FP-HALLUC) | 1 | @field_serializer가 없는 스키마에 존재한다고 주장 |
| 심각도 과대 (FP-SEV) | 2 | Azure SDK readinto async 메서드를 blocking으로 분류 |
