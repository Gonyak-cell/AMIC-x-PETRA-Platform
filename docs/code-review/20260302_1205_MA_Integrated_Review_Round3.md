# Code Review — MA Workflow Round 3 (13-Perspective Comprehensive)

> **Review Date**: 2026-03-02 12:05 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff origin/master...HEAD` — 926 source files (552 Python, 374 TypeScript)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(✅) eslint(✅) pytest(✅ 1216/1216) build(✅ 9.57s)
> **Review Gates**: Backend(FDD ✅ / KIIS ✅ / deal-mgmt ✅) Agent-Filtering(5개 호출, 0개 제외)
> **Previous Rounds**: Round 1 (22 fixed) + Round 2 (18 fixed) = 40건 기수정

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 5 | HIGH: 4 / MEDIUM: 1 | P0: 2 / P1: 3 |
| Major | 18 | HIGH: 16 / MEDIUM: 2 | P1: 10 / P2: 8 |
| **Total** | **23** | HIGH: **20** / MEDIUM: **3** | P0: **2** / P1: **13** / P2: **8** |

**FP Prevention**: 가설 35건 검증, 1건 FP 제거 (SEC-001), 2건 심각도 조정 (거부율: 8.6%)
**Cross-Verification**: Critical/Major 12건 대상, 11건 CONFIRMED, 1건 FALSE_POSITIVE

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

---

#### [R3-SEC-01] VDR `_get_and_authorize_txn` — email=None 시 접근 제어 우회 — [Critical/HIGH] — P0 (점수: 115)

- **파일**: `deal-mgmt/app/routers/vdr.py:86-95`
- **코드**:
```python
if (
    claims.role != "ADMIN"
    and claims.email is not None          # ← email=None이면 조건 전체 False
    and txn.lead_advisor_email != claims.email
    and txn.deal_captain_email != claims.email
):
    raise HTTPException(...)
```
- **위협**: ANALYST/MANAGER 역할의 JWT에 `email` 클레임이 없으면(`None`), 전체 조건이 `False`로 단락되어 403이 발생하지 않음. 비담당자가 모든 거래의 VDR에 접근 가능.
- **교차 검증**: ✅ CONFIRMED — `security.py:141-145`의 `check_client_deal_access`는 email=None을 올바르게 차단하나, VDR의 비-CLIENT 경로에는 이 검증이 없음.
- **수정 방안**:
```python
if claims.role != "ADMIN":
    if claims.email is None:
        raise HTTPException(status_code=403, detail="이 거래에 접근할 권한이 없습니다")
    if txn.lead_advisor_email != claims.email and txn.deal_captain_email != claims.email:
        raise HTTPException(status_code=403, detail="이 거래에 접근할 권한이 없습니다")
```

---

#### [R3-CODE-01] Celery 태스크 3종 예외 미처리 — DB 상태 영구 고착 — [Critical/HIGH] — P0 (점수: 115)

- **파일**: `deal-mgmt/app/tasks/fm_tasks.py:55-64, 87-92`, `deal-mgmt/app/tasks/ralph_tasks.py:27-51`, `deal-mgmt/app/tasks/marketing_tasks.py:27-55`
- **코드** (fm_tasks.py 대표):
```python
def run_finalize_and_generate_task(self, fm_id: str, transaction_id: str) -> None:
    _run_async(run_finalize_and_generate(...))
    # ← 예외 처리 없음
```
- **문제**: `extraction_tasks.py`는 `SoftTimeLimitExceeded`와 `Exception`을 모두 포착하여 DB에 `FAILED` 상태를 기록함. 그러나 `fm_tasks`, `ralph_tasks`, `marketing_tasks` 3개 파일은 예외 발생 시 DB 상태가 `PROCESSING`/`FINALIZING`으로 영구 고착됨.
- **교차 검증**: ✅ CONFIRMED — fm_tasks.py, ralph_tasks.py, marketing_tasks.py 모두 try/except 없음 확인.
- **수정 방안**: `extraction_tasks.py` 패턴 (try/except + DB 상태 마킹 + retry) 동일 적용.

---

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [R3-SEC-02] Ralph 세션 조회 — 거래 소속 검증 누락 (수평적 권한 상승) — [Major/HIGH] — P1 (점수: 85)

- **파일**: `deal-mgmt/app/routers/ralph.py:201-218`
- **코드**:
```python
@router.get("/sessions/{session_id}", response_model=RalphSessionOut)
async def get_ralph_session(session_id: uuid.UUID, ...):
    q = select(RalphSession).where(RalphSession.id == session_id)  # ← txn 소속 검증 없음
```
- **위협**: A 딜 담당 ANALYST가 B 딜의 `session_id`를 추측하여 AI 생성 문서/LLM 비용/점수 등 기밀 데이터 조회 가능.
- **교차 검증**: ✅ CONFIRMED
- **수정 방안**: `list_ralph_sessions`처럼 `transaction_id` 파라미터를 경로에 포함하거나, 조회 후 `session.transaction_id`로 접근 권한 검증.

---

#### [R3-SEC-03] VDR overview — 전체 거래 VDR 현황 집계에 거래별 접근 제어 미적용 — [Major/HIGH] — P1 (점수: 70)

- **파일**: `deal-mgmt/app/routers/vdr_overview.py:19-27`
- **위협**: CLIENT 제외 모든 인증 사용자(ANALYST 포함)가 시스템 전체 거래 VDR 현황 조회 가능. M&A 딜 목록 자체가 기밀.
- **수정 방안**: ADMIN/MANAGER 전용으로 제한하거나, 본인 담당 거래만 필터링.

---

#### [R3-SEC-04] SI 매핑 `map_si` — CLIENT 역할에 내부 SI 데이터베이스 노출 — [Major/HIGH] — P1 (점수: 70)

- **파일**: `deal-mgmt/app/routers/si_mapping.py:54-68`
- **위협**: CLIENT가 KSIC 코드 기반으로 SI 후보 기업 재무 데이터를 대량 조회 가능.
- **수정 방안**: `_READ_ACCESS`에서 CLIENT 제거. 최소 ANALYST 이상으로 제한.

---

#### [R3-FE-01] Dashboard `PhaseSummary`/`DashboardStats` — Decimal `@field_serializer` 누락 — [Major/HIGH] — P1 (점수: 85)

- **파일**: `deal-mgmt/app/schemas/dashboard.py:8-21`
- **코드**:
```python
class PhaseSummary(BaseModel):
    total_value: Decimal | None = None   # @field_serializer 없음

class DashboardStats(BaseModel):
    total_deal_value: Decimal | None = None   # @field_serializer 없음
```
- **FE 파일**: `amic-platform/src/modules/ma/types/dashboard.ts:4,10` — `string | null` 기대
- **교차 검증**: ✅ CONFIRMED — 프로젝트 패턴(Decimal→str 직렬화) 미준수. Pydantic v2 기본 동작으로 우연히 작동할 수 있으나 명시적 보장 없음.
- **수정 방안**: `@field_serializer("total_value")` / `@field_serializer("total_deal_value")` 추가.

---

#### [R3-FE-02] `dart-search` API — response_model 미정의 (`list[dict]` 반환) — [Major/HIGH] — P1 (점수: 85)

- **파일**: `deal-mgmt/app/routers/buyer_marketing.py:294-311`
- **코드**:
```python
@router.get("/buyers/dart-search")
async def dart_company_search(...) -> list[dict]:  # response_model 없음
    results = await kiis.search_company(q)
    return results[:20]
```
- **FE 파일**: `amic-platform/src/modules/ma/hooks/useDartIntegration.ts:8-20` — `DartCompanySuggestion[]` 기대
- **교차 검증**: ✅ CONFIRMED — 백엔드에 대응 Pydantic 스키마 없음. KIIS 응답 변경 시 FE 런타임 에러.
- **수정 방안**: `DartCompanySuggestionOut` 스키마 정의 + `response_model=list[DartCompanySuggestionOut]`.

---

#### [R3-FE-03] SICompany 재무 필드 10개 — FE `number` vs BE `string` 타입 불일치 — [Major/HIGH] — P1 (점수: 85)

- **FE 파일**: `amic-platform/src/modules/ma/types/si_mapping.ts:9-24` — `revenue: number | null` (10개 필드)
- **BE 파일**: `deal-mgmt/app/schemas/si_mapping.py:75-88` — `@field_serializer` → `str | None` 반환
- **영향**: SI 매핑 테이블에서 매출액/영업이익 등 10개 재무 필드가 문자열로 수신되지만 FE가 number를 기대. 산술 연산 시 NaN 또는 포맷팅 오류.
- **관련 이슈**: FE-005 (ValueChainPanel), FE-007 (FinancialSummary)도 동일 패턴.
- **수정 방안**: `si_mapping.ts`에서 Decimal 직렬화 대상 필드를 `string | null`로 변경 (프로젝트 패턴에 일관).

---

#### [R3-FE-04] `DartFinancialSummaryOut` — Decimal `@field_serializer` 누락 — [Major/HIGH] — P1 (점수: 85)

- **파일**: `deal-mgmt/app/schemas/marketing_log.py:47-55`
- **코드**: `revenue`, `operating_profit`, `net_income`, `debt_ratio` 4개 Decimal 필드에 serializer 없음.
- **2개 에이전트 교차 발견**: Python Code Reviewer (W-06) + FE Auditor (FE-006)
- **수정 방안**: `@field_serializer("revenue", "operating_profit", "net_income", "debt_ratio")` 추가.

---

#### [R3-FE-05] `TransactionCreate` — Deal Terms 11개 필드 FE 타입 누락 — [Major/HIGH] — P1 (점수: 85)

- **BE 파일**: `deal-mgmt/app/schemas/transaction.py:76-87` — 11개 Optional 필드 존재
- **FE 파일**: `amic-platform/src/modules/ma/types/transaction.ts:87-102` — Deal Terms 필드 없음
- **교차 검증**: ✅ CONFIRMED — 모든 필드 Optional이므로 API는 동작하지만, FE에서 거래 생성 시 초기값 설정 불가.
- **수정 방안**: `TransactionCreate` 인터페이스에 11개 옵셔널 필드 추가.

---

#### [R3-PERF-01] SI 매핑 — 최대 10,000건 ORM 전체 메모리 로드 — [Critical/MEDIUM ⚠️] — P1 (점수: 60)

- **파일**: `deal-mgmt/app/services/si_mapping_service.py:534-565`
- ⚠️ 이 Critical 이슈는 MEDIUM 신뢰도로 인해 P1으로 분류됨 (실사용 규모 의존적).
- **수정 방안**: 필요 컬럼만 SELECT하는 row-level 쿼리 전환, GIN 인덱스 추가.

---

#### [R3-PERF-02] `SICompany` — `revenue`, `has_investment_history` 필터 인덱스 누락 — [Major/HIGH] — P1 (점수: 70)

- **파일**: `deal-mgmt/app/models/si_company.py:40,109`
- **문제**: SI 매핑 쿼리의 WHERE 조건에 사용되나 인덱스 없음. 10,000건 풀스캔.
- **수정 방안**: `__table_args__`에 `Index("ix_si_company_revenue", "revenue")` 등 추가.

---

#### [R3-CODE-02] Audit CSV 내보내기 — 10,000건 단일 메모리 로드 — [Major/HIGH] — P1 (점수: 70)

- **파일**: `deal-mgmt/app/routers/audit.py:61-68`
- **문제**: `limit=10000`으로 단일 쿼리. JSONB `old_value`/`new_value` 포함 시 수십 MB.
- **수정 방안**: StreamingResponse + 페이지 단위 yield.

---

#### [R3-CODE-03] consortium.py — 5개 엔드포인트에서 transaction 존재 검증 누락 — [Major/HIGH] — P1 (점수: 70)

- **파일**: `deal-mgmt/app/routers/consortium.py:77-98`
- **문제**: `buyers.py`와 달리 `get_transaction(db, txn_id)` 호출 없이 `check_client_deal_access`만 호출.
- **수정 방안**: 각 엔드포인트에 `await transaction_service.get_transaction(db, txn_id)` 추가.

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [R3-PERF-03] `BuyerMarketingLog` — `(buyer_id, transaction_id)` 복합 인덱스 누락 — [Major/HIGH] — P2 (점수: 55)

- **파일**: `deal-mgmt/app/models/buyer_marketing_log.py:17-29`
- **문제**: 단일 인덱스 2개 존재하나, 빈번한 `WHERE buyer_id = ? AND transaction_id = ?` 조합 쿼리에 복합 인덱스 없음.
- **수정 방안**: `__table_args__`에 복합 인덱스 추가.

---

#### [R3-PERF-04] `promote_short_list` — 루프 내 N회 audit_service.record 호출 — [Major/HIGH] — P2 (점수: 55)

- **파일**: `deal-mgmt/app/routers/buyers.py:221-233`
- **문제**: 30명 승격 시 30개 INSERT 개별 실행. `si_mapping_service.bulk_add_to_buyers`도 동일.
- **수정 방안**: `db.add_all(logs)` 배치 처리.

---

#### [R3-PERF-05] `get_deep_dive` — JWT 토큰 매 호출마다 신규 생성 — [Major/HIGH] — P2 (점수: 55)

- **파일**: `deal-mgmt/app/services/si_mapping_service.py:287-298`
- **문제**: 30초 TTL JWT를 매 API 호출마다 새로 생성. 딥다이브 1회 = 6회 HTTP.
- **수정 방안**: TTL 캐싱(20초 내 재사용).

---

#### [R3-SEC-05] `document_extraction_service` — `target_model` Literal 제한 없음 — [Major/MEDIUM] — P2 (점수: 42)

- **파일**: `deal-mgmt/app/services/document_extraction_service.py:594-613`
- **수정 방안**: `ExtractionConfirmRequest`에서 `target_model: Literal["nda", "bid", "contract", "transaction"]`.

---

#### [R3-SEC-06] `blob_storage.py` — `download_blob_to_file` 로컬 모드 경로 순회 검증 누락 — [Major/MEDIUM] — P2 (점수: 42)

- **파일**: `deal-mgmt/app/core/blob_storage.py:132-153`
- **수정 방안**: `src.resolve().startswith(_LOCAL_STORAGE_DIR.resolve())` 검증 추가.

---

#### [R3-PERF-06] `remove_buyer` — 삭제 시 불필요한 COUNT 쿼리 2회 — [Major/HIGH] — P2 (점수: 55)

- **파일**: `deal-mgmt/app/routers/buyers.py:381-392`
- **수정 방안**: 감사 notes에 고정 문자열 사용, COUNT 제거.

---

#### [R3-PERF-07] `BuyerMarketingLog.log_date` — String(10)을 정렬/집계에 사용 — [Major/MEDIUM] — P2 (점수: 42)

- **파일**: `deal-mgmt/app/models/buyer_marketing_log.py:31`
- **문제**: YYYY-MM-DD String 컬럼에 `ORDER BY DESC`, `func.max()` 적용. 인덱스 없음.
- **수정 방안**: `log_date`에 인덱스 추가 (단기). Date 타입 변환 (중기).

---

## Migration Issues (기존 마이그레이션 — 참고용)

> 아래 이슈들은 이미 프로덕션에 적용된 마이그레이션에 관한 것으로, 직접 수정 시 위험. 신규 마이그레이션 작성 시 참고.

| ID | 파일 | 문제 | 심각도 |
|----|------|------|--------|
| MIG-001 | `048_pef_gp_indexes.py` | 파일명 048 중복 (revision은 048b) | Major |
| MIG-002 | 7개 파일 (010~027) | JSONB 직접 사용 (conftest 몽키패치로 CI 통과) | Design Risk |
| MIG-003 | 001, 002 | 금액 컬럼 NUMERIC(20,2) — 프로젝트 기준 (20,4) 미충족 | Major |
| MIG-004 | 037 | downgrade() pass — 독립 롤백 불가 | Major |
| MIG-005 | 051, 005 | enum ADD VALUE downgrade 불가 (PostgreSQL 제한) | Design Risk |
| MIG-006 | 035 | 비가역적 DELETE — 백업 없이 데이터 손실 가능 | Major |
| MIG-007 | 014 | downgrade `drop_index` table_name 누락 3건 | Major |
| MIG-008 | 016 | downgrade `drop_index` table_name 누락 8건 | Major |
| MIG-009 | 028 | downgrade 시 LAW_FIRM 레코드 미처리 | Major |

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)
1. [R3-SEC-01] VDR email=None 접근 제어 우회 — `vdr.py` (점수: 115)
2. [R3-CODE-01] Celery 태스크 3종 예외 미처리 → DB 상태 고착 — `fm_tasks.py`, `ralph_tasks.py`, `marketing_tasks.py` (점수: 115)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)
1. [R3-SEC-02] Ralph 세션 거래 소속 검증 누락 — `ralph.py` (점수: 85)
2. [R3-FE-01] Dashboard Decimal serializer 누락 — `dashboard.py` (점수: 85)
3. [R3-FE-02] dart-search response_model 미정의 — `buyer_marketing.py` (점수: 85)
4. [R3-FE-03] SICompany 10개 필드 number vs string — `si_mapping.ts` (점수: 85)
5. [R3-FE-04] DartFinancialSummaryOut Decimal serializer 누락 — `marketing_log.py` (점수: 85)
6. [R3-FE-05] TransactionCreate Deal Terms 11개 필드 누락 — `transaction.ts` (점수: 85)
7. [R3-SEC-03] VDR overview 접근 제어 미적용 — `vdr_overview.py` (점수: 70)
8. [R3-SEC-04] SI 매핑 CLIENT 접근 허용 — `si_mapping.py` (점수: 70)
9. [R3-CODE-02] Audit CSV 10,000건 메모리 로드 — `audit.py` (점수: 70)
10. [R3-CODE-03] consortium.py transaction 검증 누락 — `consortium.py` (점수: 70)
11. [R3-PERF-01] SI 10,000건 ORM 로드 ⚠️ — `si_mapping_service.py` (점수: 60, Critical→P1)
12. [R3-PERF-02] SICompany 필터 인덱스 누락 — `si_company.py` (점수: 70)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [R3-PERF-03] BuyerMarketingLog 복합 인덱스 — `buyer_marketing_log.py` (점수: 55)
2. [R3-PERF-04] promote_short_list N+1 audit — `buyers.py` (점수: 55)
3. [R3-PERF-05] JWT 매 호출 생성 — `si_mapping_service.py` (점수: 55)
4. [R3-PERF-06] remove_buyer 불필요 COUNT — `buyers.py` (점수: 55)
5. [R3-SEC-05] target_model Literal 제한 — `document_extraction_service.py` (점수: 42)
6. [R3-SEC-06] download_blob_to_file 경로 순회 — `blob_storage.py` (점수: 42)
7. [R3-PERF-07] log_date String 정렬 — `buyer_marketing_log.py` (점수: 42)

---

## Methodology

- **Agents**: python-code-reviewer, backend-security-reviewer, migration-validator, performance-profiler, general-purpose (FE type + API audit)
- **Files scanned**: 926 (552 Python + 374 TypeScript)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 12건 → 11 CONFIRMED, 1 FALSE_POSITIVE
- **Backend availability**: FDD(✅) KIIS(✅) deal-mgmt(✅)

## 검증 투명성

### 검증 통계
- 검증한 가설: 35건
- 거부된 가설 (사전 제거): 3건
- 보고된 이슈: 23건 + 9건 마이그레이션 참고
- 거부율: 8.6%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | SEC-001: .env가 git에 트래킹되지 않음 (git ls-files 확인) |
| 심각도 재조정 | 2 | PERF-03: func.lower 인덱스 우회 → txn_id 인덱스로 실제 영향 미미; FE-02: Optional 필드로 런타임 오류 아님 |

### 누적 리뷰 결과 (3라운드 합계)

| Round | 발견 | 수정 | FP 제거 |
|-------|------|------|--------|
| Round 1 | 30 | 22 | 0 |
| Round 2 | 30 (raw) → 18 (confirmed) | 18 | 12 |
| Round 3 | 35 (raw) → 23 (confirmed) | — | 3 |
| **합계** | **95 → 63** | **40** | **15** |
