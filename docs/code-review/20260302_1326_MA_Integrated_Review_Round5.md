# Code Review — MA Workflow Round 5 (미수행 관점 통합 리뷰)

> **Review Date**: 2026-03-02 13:26 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: deal-mgmt/ + amic-platform/src/modules/ma/ — `git diff master` 변경 파일 전체
> **Method**: 5-Agent Parallel Review + Cross-Verification
> **Agents**: Error Handling, Test Quality, Build/CI Integrity, Architecture, FE State/Hooks
> **Round**: 5 (Rounds 1-4에서 미수행된 5개 관점 보완)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 9     | HIGH: 9                | P0: 9                |
| Major    | 22    | HIGH: 19 / MEDIUM: 3   | P1: 19 / P2: 3      |
| Moderate | 4     | HIGH: 2 / MEDIUM: 2    | P2: 2 / P3: 2       |
| **Total**| **35**| HIGH: **30** / MEDIUM: **5** | P0: **9** / P1: **19** / P2: **5** / P3: **2** |

**FP Prevention**: 5개 에이전트 병렬 실행, Critical/Major 전건 코드 Read 교차 검증
**Cross-Verified**: 3건 (TransactionWorkspacePage God Component — 3 에이전트, useCreateExtraction onError — 3 에이전트)

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

#### [R5-CI-01] deploy.yml에 deal-mgmt Celery Worker 누락 — Critical/HIGH (점수: 100)

**파일**: `.github/workflows/deploy.yml:119, 124, 133`

**증거**:
- line 119 (`all` scope): `"frontend nginx fdd-api kiis-api im-api im-celery-worker im-celery-beat deal-mgmt-api"` — `deal-mgmt-celery-worker` 누락
- line 124 (`backend-only`): 동일하게 누락
- line 133 (`auto` detect): `deal-mgmt/` 변경 시 `deal-mgmt-api`만 추가, Celery worker 누락
- IM 모듈은 line 132에서 `im-celery-worker im-celery-beat` 올바르게 포함

**영향**: deal-mgmt 코드 변경 배포 시 Celery worker는 이전 이미지로 실행. 문서 추출, VDR 파싱, FM 생성 등 비동기 태스크가 새 코드와 불일치하여 런타임 에러 발생.

---

#### [R5-CI-02] deal-mgmt Celery/Redis 프로덕션 설정 누락 — Critical/HIGH (점수: 100)

**파일**: `docker-compose.prod.yml` (전체)

**증거**:
- `deal-mgmt-celery-worker`, `deal-mgmt-redis` 프로덕션 오버라이드 없음
- KIIS Redis: `--requirepass ${KIIS_REDIS_PASSWORD}` (line 128-131) ✓
- IM Redis: `--requirepass ${IM_REDIS_PASSWORD}` (line 207-208) ✓
- deal-mgmt Redis: 비밀번호 없이 실행 ✗
- deal-mgmt-api prod 환경변수에 `REDIS_URL`, `REDIS_RESULT_BACKEND` 미설정

**영향**: 프로덕션 Redis가 비밀번호 없이 노출. Celery worker에 restart/memory 제한 미설정으로 OOM 시 복구 불가.

---

#### [R5-TEST-01] deal_clients.py 라우터 테스트 0% — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/routers/deal_clients.py` — `test_deal_clients.py` 미존재

CLIENT 역할 사용자의 딜 접근 권한 할당/해제 3개 엔드포인트, 중복 이메일 탐지 로직 전부 미검증.

---

#### [R5-BUG-01] deal_clients.py `Transaction.codename` AttributeError — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/routers/deal_clients.py:135`

**증거**:
- line 135: `select(DealClient, Transaction.name, Transaction.codename)` — `codename` 사용
- 모델 `deal-mgmt/app/models/transaction.py:18`: `code_name: Mapped[str]` — `code_name` (언더스코어 있음)

`GET /deal-clients/by-email` 호출 시 `AttributeError: type object 'Transaction' has no attribute 'codename'`로 500 에러 즉시 발생. 테스트 0%(R5-TEST-01)이므로 미발견.

---

#### [R5-TEST-02] client_portal.py 라우터 테스트 0% — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/routers/client_portal.py` — `test_client_portal.py` 미존재

CLIENT 대시보드에서 민감한 딜 데이터(바이어 파이프라인, 미팅, 마케팅 배포)를 5+ SQL 쿼리로 집계하여 반환. 클라이언트 격리 검증 0%.

---

#### [R5-TEST-03] vdr_internal.py 라우터 테스트 0% — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/routers/vdr_internal.py` — `test_vdr_internal.py` 미존재

HMAC 기반 서비스간 인증(`_verify_internal_key`), 파일 바이트 다운로드 엔드포인트 전부 미검증.

---

#### [R5-TEST-04] dashboard.py 라우터 테스트 0% — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/routers/dashboard.py` — `test_dashboard.py` 미존재

CLIENT 역할 제외 로직(line 30-31), Decimal 딜 가치 집계 미검증.

---

#### [R5-TEST-05] transcription.py 라우터 테스트 0% — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/routers/transcription.py` — `test_transcription.py` 미존재

오디오 파일 업로드, 파일 타입/크기 검증, LLM 기반 미팅 로그 생성 전부 미검증.

---

#### [R5-ARCH-01] TransactionWorkspacePage God Component (6,236줄) — Critical/HIGH (점수: 110, 3-에이전트 교차 확인)

**파일**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx`

**증거** (3개 에이전트 일치):
- **Architecture Agent**: 6,236줄, 55+ useState, 47+ custom hooks
- **FE Agent 5a**: 35+ useQuery 무조건 마운트, 탭 무관하게 전체 데이터 fetch
- **FE Agent 5b**: 40+ hooks, 20+ useState, 폼 상태 탭 전환 시 잔존

**영향**:
1. Overview 탭만 봐도 ~35개 API 동시 호출 (NDA, Bid, DD, Contract, Closing, PMI 등)
2. 어느 쿼리든 상태 변경 시 6,236줄 전체 리렌더링
3. 4개 훅에 polling 활성 → 비활성 탭에서도 불필요한 주기적 refetch
4. 테스트 불가능 — 개별 탭 기능의 단위 테스트 불가

---

### P1 — 스프린트 우선 (점수: 60-89)

#### [R5-ERR-01] VDR 업로드: blob 업로드 후 DB commit 실패 시 orphan blob — Major/HIGH (70)

**파일**: `deal-mgmt/app/services/vdr_service.py:218-233`

blob 업로드(218) → DB add+commit(232-233). commit 실패 시 blob은 Azure에 잔존하되 DB에 참조 없음.

---

#### [R5-ERR-02] Approval 동시 투표 시 JSONB 덮어쓰기 race condition — Major/HIGH (70)

**파일**: `deal-mgmt/app/routers/approvals.py:138-187`

`_get_approval_or_404`에 `with_for_update()` 없음. 두 승인자가 동시 투표 시 마지막 commit이 첫 번째 결정을 덮어씀.

---

#### [R5-ERR-03] useCreateExtraction onError 핸들러 누락 — Major/HIGH (80, 교차 확인)

**파일**: `amic-platform/src/modules/ma/hooks/useDocumentExtraction.ts:64-82`

`onSuccess` 있으나 `onError` 없음. 409 Conflict(중복 추출) 또는 서버 에러 시 사용자 피드백 0. 같은 파일의 `useBatchExtract`, `useConfirmExtraction`은 onError 구현됨.

---

#### [R5-ERR-05] FM Finalize: Celery 태스크 실패 시 FINALIZING 상태 고착 — Major/MEDIUM (42) → P2

**파일**: `deal-mgmt/app/routers/financial_models.py:211-219` + `deal-mgmt/app/tasks/fm_tasks.py:82-108`

FM 상태를 FINALIZING으로 commit(212) 후 Celery task dispatch(216). SoftTimeLimitExceeded는 warning 로그만, 일반 Exception은 max_retries=1 후 포기. 상태 롤백 로직 없음.

---

#### [R5-ERR-06] Azure blob 예외 미처리 — VDR 업로드/다운로드 — Major/HIGH (70)

**파일**: `deal-mgmt/app/services/vdr_service.py:218` + `deal-mgmt/app/core/blob_storage.py`

Azure SDK 예외(BlobStorageError, ResourceNotFoundError)가 vdr_service에서 catch 없이 전파. 사용자에게 500 Internal Server Error로 표시.

---

#### [R5-CI-03] Node.js 버전 불일치: CI(22) vs Docker(20) — Major/HIGH (70)

**파일**: `.github/workflows/ci.yml:18` vs `amic-platform/Dockerfile:9`

CI에서 Node 22로 테스트, 프로덕션 Docker는 `node:20-alpine`. Node 22 전용 API 사용 시 프로덕션 런타임 에러.

---

#### [R5-CI-04] KIIS CI에 Ruff Lint 단계 누락 — Major/HIGH (70)

**파일**: `.github/workflows/ci.yml:100-130`

deal-mgmt, FDD는 `ruff check` 포함. KIIS는 auth guard 테스트와 corp basic 테스트만 실행.

---

#### [R5-CI-05] IM/FDD CI 검사 `|| true`로 무효화 — Major/HIGH (70)

**파일**: `.github/workflows/ci.yml:153, 176, 178`

IM ruff(176), IM pytest(178), FDD pytest(153) 모두 `|| true`. 실패해도 CI pass.

---

#### [R5-CI-06] Python 버전 불일치: CI(3.12) vs Docker(3.11) — Major/HIGH (70)

**파일**: `.github/workflows/ci.yml:19` vs `deal-mgmt/Dockerfile` + `kiis/Dockerfile`

deal-mgmt, KIIS는 CI에서 Python 3.12로 테스트하지만 Docker에서 3.11로 실행. 3.12 전용 문법(type 문) 사용 시 프로덕션 SyntaxError.

---

#### [R5-TEST-06] conftest.py 항상 ADMIN 모킹 — 비-CLIENT 역할 접근 제어 미검증 — Major/HIGH (70)

**파일**: `deal-mgmt/tests/conftest.py:98-106`

`MOCK_CLAIMS = JWTClaims(role="ADMIN")`. ANALYST, MANAGER 역할의 접근 제한이 한 번도 테스트되지 않음. `require_role("ADMIN", "MANAGER")`인 5개 엔드포인트에서 ANALYST 차단 미검증.

---

#### [R5-TEST-07] Buyer status 잘못된 전이 미테스트 — Major/HIGH (70)

**파일**: `deal-mgmt/tests/test_buyers.py`

정상 전이(forward chain)만 테스트. IDENTIFIED → NDA_SIGNED(단계 건너뛰기), SELECTED → IDENTIFIED(역전이) 등 **차단되어야 하는 전이**가 0건 테스트됨.

---

#### [R5-TEST-09] PEF registry + FI 추천 알고리즘 테스트 0% — Major/HIGH (70)

**파일**: `deal-mgmt/app/routers/pef_registry.py` — `test_pef*.py` 미존재

GP 그룹핑, 펀드 사이즈 범위 매칭, 중복 제거, Decimal 포맷팅 전부 미검증.

---

#### [R5-TEST-10] timeline.py 라우터 테스트 0% — Major/HIGH (70)

**파일**: `deal-mgmt/app/routers/timeline.py` — `test_timeline.py` 미존재

Gantt 차트 문자열 파싱(`title.split(" -> ")`) 로직, CRUD, 자동 생성 이벤트 보호 미검증.

---

#### [R5-TEST-11] SQLite/PostgreSQL 테스트-프로덕션 괴리 — Major/HIGH (70)

**파일**: `deal-mgmt/tests/conftest.py:65-66`

`visit_JSONB → "JSON"`, `visit_UUID → "CHAR(36)"` 심. JSONB `@>` 연산자, UUID 대소문자 비교 등 PostgreSQL 특유 동작 미검증. 아키텍처적 수용 사항이나 리스크 존재.

---

#### [R5-TEST-12] document_extraction HTTP 수준 통합 테스트 없음 — Major/HIGH (70)

**파일**: `deal-mgmt/tests/test_document_extraction_service.py`

서비스 레이어 단위 테스트만 존재. HTTP 엔드포인트(409 Conflict, batch 최대 10건, 재확인 감사 추적) 미검증.

---

#### [R5-ARCH-02] 트랜잭션 소유권 불일치 (Dual-Commit 패턴) — Major/HIGH (70)

**파일**: 30개 라우터 + 13개 서비스

일부 서비스(`transaction_service`)는 내부에서 commit, 다른 라우터(`buyers`, `bids`, `closing` 등)는 라우터에서 직접 flush+commit. 다중 서비스 호출 시 첫 번째 커밋 후 두 번째 실패 시 부분 커밋 잔존.

---

#### [R5-ARCH-03] 서비스 레이어에서 HTTPException 직접 raise — Major/HIGH (70)

**파일**: `transaction_service.py:7`, `rfi_service.py:8`, `financial_model_service.py:9`, `si_mapping_service.py:15`

서비스가 FastAPI HTTPException을 직접 raise. Celery 태스크나 다른 서비스에서 호출 시 HTTP 컨텍스트 없어 비정상 종료. `core/exceptions.py`에 도메인 예외 이미 정의됨(`WorkflowError`, `DocumentNotFoundError` 등).

---

#### [R5-FE-02] useSyncRFIToChecklists: DD 체크리스트 캐시 무효화 누락 — Major/HIGH (70)

**파일**: `amic-platform/src/modules/ma/hooks/useRFI.ts:357-375`

`onSuccess`에서 `rfiKeys(txnId)`만 무효화. RFI→DD 체크리스트 동기화 후 DD 탭이 stale 데이터 표시. `["ma", "transactions", txnId, "dd-checklist"]` 무효화 추가 필요.

---

#### [R5-FE-04] useUpdateFMChecklistItem onError/toast 누락 — Major/HIGH (70)

**파일**: `amic-platform/src/modules/ma/hooks/useFMChecklist.ts:29-49`

같은 파일의 `useBulkUpdateFMItems`, `useFinalizeFMChecklist`은 onError 구현됨. 개별 항목 업데이트만 누락.

---

#### [R5-FE-05] useLDDReports 4개 mutation onError 누락 — Major/HIGH (70)

**파일**: `amic-platform/src/modules/ma/hooks/useLDDReports.ts:196-306`

`useReviewLDDItem`, `useBulkReviewLDD`, `useAddLDDReference`, `useRemoveLDDReference` 4개 mutation에 onError 없음. 같은 파일의 `useCreateLDDFromVdr`, `useFinalizeLDD`는 구현됨.

---

#### [R5-FE-06] useDecideApproval/useCancelApproval `["ma"]` 전체 무효화 — Major/HIGH (70)

**파일**: `amic-platform/src/modules/ma/hooks/useApprovals.ts:79-120`

승인 결정 1건에 MA 모듈 전체 쿼리(transactions, buyers, ndas, bids, dd, contracts 등 수십 개) 무효화. 범위를 `["ma", "transactions", txnId, "approvals"]`로 좁혀야 함.

---

#### [R5-FE-07] TransactionListPage KPI가 현재 페이지 슬라이스로 계산 — Major/HIGH (70)

**파일**: `amic-platform/src/modules/ma/pages/TransactionListPage.tsx:114-123`

`items`(pageSize=20)로 "진행 중", "예상 총액", "이번 달" KPI 계산. 100개 거래 중 첫 20개만으로 집계하여 수치 부정확. `total`만 서버 전체 값.

---

### P2 — 개선 권장 (점수: 30-59)

#### [R5-ERR-05] FM FINALIZING 상태 고착 — Major/MEDIUM (42)

위 P1 항목 참조. 신뢰도 MEDIUM으로 P2 분류.

---

#### [R5-ARCH-04] 모듈 레벨 싱글턴 동기화 없음 — Major/MEDIUM (42)

**파일**: `contract_generation_service.py:349`, `spa_analysis_service.py:90`, `si_mapping_service.py:287`

`_llm_client`, `_service_token_cache` global 변수에 `asyncio.Lock()` 없음. 같은 파일의 `_kiis_http_client`는 Lock 사용.

---

#### [R5-FE-03] FIRecommendModal 동시 mutation — Major/MEDIUM (42)

**파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:56-83`

`Promise.allSettled`로 N개 `addBuyer.mutateAsync` 동시 호출. 개별 onError 토스트 + 요약 토스트 중복.

---

#### [R5-FE-08] useUpdateDistribution 반환값 미사용 — Moderate/HIGH (40)

**파일**: `TransactionWorkspacePage.tsx:527` — `useUpdateDistribution(id);` 호출만, 반환값 미할당.

---

#### [R5-FE-09] usePromoteShortList onSuccess toast 누락 — Moderate/HIGH (40)

**파일**: `amic-platform/src/modules/ma/hooks/usePefRegistry.ts:70-89` — 모듈 전체 50+ mutation 중 유일하게 성공 toast 없음.

---

### P3 — 저우선 (점수: <30)

#### [R5-FE-10] useWorkingGroup 호출 결과 미사용 — Moderate/MEDIUM (24)

**파일**: `TransactionWorkspacePage.tsx:492` — `useWorkingGroup(id);` 반환값 미구조분해.

---

#### [R5-FE-11] staleTime 미설정 쿼리 30+개 — Moderate/MEDIUM (24)

33개 훅 파일 중 8개만 staleTime 설정. 나머지 30+개는 default 0으로 window focus마다 전부 refetch.

---

## Priority Matrix

### P0 — 즉시 수정 (9건)
1. [R5-BUG-01] deal_clients.py `Transaction.codename` AttributeError — `deal_clients.py:135` (100)
2. [R5-CI-01] deploy.yml deal-mgmt Celery Worker 누락 — `.github/workflows/deploy.yml` (100)
3. [R5-CI-02] deal-mgmt Celery/Redis prod 설정 누락 — `docker-compose.prod.yml` (100)
4. [R5-ARCH-01] TransactionWorkspacePage God Component — `TransactionWorkspacePage.tsx` (110, 3-에이전트)
5. [R5-TEST-01] deal_clients.py 테스트 0% (100)
6. [R5-TEST-02] client_portal.py 테스트 0% (100)
7. [R5-TEST-03] vdr_internal.py 테스트 0% (100)
8. [R5-TEST-04] dashboard.py 테스트 0% (100)
9. [R5-TEST-05] transcription.py 테스트 0% (100)

### P1 — 스프린트 우선 (19건)
1. [R5-ERR-03] useCreateExtraction onError 누락 (80, 교차 확인)
2. [R5-ERR-01] VDR orphan blob (70)
3. [R5-ERR-02] Approval JSONB race condition (70)
4. [R5-ERR-06] Azure blob 예외 미처리 (70)
5. [R5-CI-03] Node.js 22 vs 20 불일치 (70)
6. [R5-CI-04] KIIS CI lint 누락 (70)
7. [R5-CI-05] IM/FDD CI `|| true` (70)
8. [R5-CI-06] Python 3.12 vs 3.11 불일치 (70)
9. [R5-TEST-06] conftest ADMIN 고정 (70)
10. [R5-TEST-07] Buyer invalid transition 미테스트 (70)
11. [R5-TEST-09] PEF/FI 추천 테스트 0% (70)
12. [R5-TEST-10] timeline 테스트 0% (70)
13. [R5-TEST-12] extraction HTTP 통합 테스트 없음 (70)
14. [R5-ARCH-02] Dual-commit 패턴 (70)
15. [R5-ARCH-03] 서비스에서 HTTPException raise (70)
16. [R5-FE-02] RFI→DD 캐시 무효화 누락 (70)
17. [R5-FE-04] FM Checklist onError 누락 (70)
18. [R5-FE-05] LDD Reports 4개 onError 누락 (70)
19. [R5-FE-06] Approval `["ma"]` 과도한 무효화 (70)
20. [R5-FE-07] TransactionListPage KPI 부정확 (70)

### P2 — 개선 권장 (5건)
1. [R5-ERR-05] FM FINALIZING 고착 (42)
2. [R5-ARCH-04] 모듈 레벨 싱글턴 Lock 없음 (42)
3. [R5-FE-03] FI 모달 동시 mutation 토스트 (42)
4. [R5-FE-08] useUpdateDistribution 미사용 (40)
5. [R5-FE-09] usePromoteShortList toast 누락 (40)

### P3 — 저우선 (2건)
1. [R5-FE-10] useWorkingGroup 미사용 (24)
2. [R5-FE-11] staleTime 미설정 30+ 쿼리 (24)

---

## Methodology

- **Agents used**: Error Handling & Resilience, Test Quality, Build/CI Integrity, Architecture & Design Pattern, FE State Management & Hooks (×2)
- **Files scanned**: ~580 (deal-mgmt 46 routers + 35 services + 57 models + tests, amic-platform 33 hooks + 3 pages + 90+ components, CI/Docker config)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 전건 코드 Read 검증 완료
- **FP Prevention**: 반증된 가설 보고 제외 (FE 에이전트 10건, Architecture 에이전트 4건 사전 거부)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: ~55건
- 거부된 가설 (사전 제거): ~14건
- 보고된 이슈: 34건
- 거부율: 25%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 5 | "onError 전반 누락" → 50+ 중 6건만 누락 확인 |
| 범위 외 | 3 | 프론트엔드 전용 이슈이나 백엔드 관점 에이전트 보고 |
| 이미 수정됨 | 2 | Round 4에서 수정된 항목 재보고 |
| 오판 | 2 | 아키텍처 결정으로 의도된 패턴 |
| 중복 | 2 | 복수 에이전트 동일 이슈 (God Component, useCreateExtraction) |

---

## Round 5 범위 선정 근거

| 관점 | Round 1-4 커버리지 | Round 5 수행 |
|------|-------------------|-------------|
| 보안 | ✅ Round 1,2,4 | - |
| API 계약 | ✅ Round 3,4 | - |
| 성능 | ✅ Round 4 | - |
| 마이그레이션 | ✅ Round 2,3 | - |
| Python 코드 품질 | ✅ Round 1,3 | - |
| 타입 안전성 | ✅ Round 3,4 | - |
| **에러 처리/복원력** | ❌ | ✅ 6건 발견 |
| **테스트 품질** | ❌ | ✅ 12건 발견 |
| **FE 상태/훅 패턴** | ❌ | ✅ 10건 발견 |
| **아키텍처/설계** | ❌ | ✅ 4건 발견 |
| **빌드/CI 무결성** | ❌ | ✅ 6건 발견 |
