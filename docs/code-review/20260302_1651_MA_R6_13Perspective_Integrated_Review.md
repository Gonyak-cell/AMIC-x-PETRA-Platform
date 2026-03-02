# Code Review — Round 6: 13-Perspective Integrated Review

> **Review Date**: 2026-03-02 16:51
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Uncommitted changes vs HEAD (49 modified + 11 new files)
> **Method**: Quality Gates + 5-Agent Parallel Review + Cross-Verification
> **Quality Gates**: ruff(✅) tsc(✅) pytest(1290/1296 ✅)
> **Agents**: Error/Edge/Security, FE State/Hook/Cache, CI/Infra/Deploy, Test Quality, Architecture/Type

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Critical | 1 | HIGH: 1 | P0: 1 |
| Major | 14 | HIGH: 10 / MEDIUM: 4 | P1: 10 / P2: 4 |
| **Total** | **15** | HIGH: **11** / MEDIUM: **4** | P0: **1** / P1: **10** / P2: **4** |

**교차 검증**: 3건 2+ 에이전트 동시 발견 (R6-API-01, R6-BLOB-01, R6-KPI-01)
**허위 양성 방지**: 가설 28건 검증, 13건 사전 거부 (거부율: 46%)

---

## Findings

### P0 — 즉시 수정 (배포 실패 방지)

#### [R6-DEPLOY-01] deploy.yml 검증 게이트에 Redis 비밀번호 4종 누락 — [Critical/HIGH] — Score: 110

**위치**: `.github/workflows/deploy.yml:148-163`

**문제**: `docker-compose.prod.yml`에서 `${MA_REDIS_PASSWORD:?}`, `${KIIS_REDIS_PASSWORD:?}`, `${KIIS_ES_PASSWORD:?}`, `${IM_REDIS_PASSWORD:?}` 가 `:?` 구문으로 강제됨. 그러나 deploy.yml의 환경변수 검증 게이트(149-152행)에는 이 4종이 **누락**.

**영향**: 프로덕션 `.env`에 Redis 비밀번호가 없으면 검증 게이트는 통과하지만, `docker compose up`에서 `:?` 구문이 터지며 **모든 서비스가 기동 실패**.

**수정**: 검증 게이트에 `MA_REDIS_PASSWORD`, `KIIS_REDIS_PASSWORD`, `KIIS_ES_PASSWORD`, `IM_REDIS_PASSWORD` 추가.

---

### P1 — 스프린트 우선

#### [R6-API-01] `ApprovalDecision.email` 필수 필드가 서버에서 무시됨 (데드 코드) — [Major/HIGH] — Score: 80

**교차 검증**: 3개 에이전트 동시 발견 (Error/Security, FE, Architecture)

**위치**: `deal-mgmt/app/schemas/approval.py:47-50` + `deal-mgmt/app/routers/approvals.py:150`

**문제**: `decide_approval`이 `claims.email`로 승인자를 식별하도록 변경되었으나, `ApprovalDecision` 스키마에 `email: str`이 **필수 필드**로 남아있음. 서버가 완전히 무시하는 필드를 클라이언트가 반드시 보내야 함.

**수정**: `ApprovalDecision.email`을 `str | None = None`으로 변경하거나 제거. 프론트엔드 `ApprovalDecision` 타입도 동기화.

#### [R6-BLOB-01] `delete_blob` Azure 모드 — 존재하지 않는 blob 삭제 시 예외 발생 — [Major/HIGH] — Score: 80

**교차 검증**: 2개 에이전트 동시 발견 (Error/Security, Architecture)

**위치**: `deal-mgmt/app/core/blob_storage.py:168-169`

**문제**: docstring은 "존재하지 않아도 에러를 발생시키지 않는다"라고 약속하지만, Azure 모드에서 `blob.delete_blob()` 호출 시 `ResourceNotFoundError` 발생. orphan blob 정리 시 이미 삭제된 blob에 대해 호출하면 원래 예외가 마스킹됨.

**수정**: `try/except`로 not found 에러 무시 또는 `delete_if_exists=True` 사용.

#### [R6-KPI-01] TransactionListPage 이중 API 호출 (KPI용 limit=1000) — [Major/HIGH] — Score: 80

**교차 검증**: 2개 에이전트 동시 발견 (FE, Architecture)

**위치**: `amic-platform/src/modules/ma/pages/TransactionListPage.tsx:110`

**문제**: KPI 계산을 위해 `useTransactions({ limit: 1000, offset: 0 })`를 별도 호출. 매 마운트마다 2개 API 동시 호출, 1000건 초과 시 KPI 부정확.

**수정**: 서버 전용 KPI 엔드포인트 (`GET /transactions/stats`) 분리 권장. 또는 `staleTime: 60_000` 추가.

#### [R6-FE-01] `useConfirmExtraction` naive pluralization — 잘못된 query key 생성 — [Major/HIGH] — Score: 70

**위치**: `amic-platform/src/modules/ma/hooks/useDocumentExtraction.ts:141-156`

**문제**: `${data.target_model}s` 단순 복수형 변환이 `dd-checklist`, `closing`, `compliance`, `earnout`, `pmi` 등의 실제 query key와 불일치. 해당 모델 타입의 추출 확정 후 캐시가 무효화되지 않아 stale data 표시.

**수정**: `TARGET_MODEL_TO_QUERY_KEY` 매핑 객체 사용.

#### [R6-INFRA-01] celery-worker JWT_SECRET 환경변수 불일치 — [Major/HIGH] — Score: 70

**위치**: `docker-compose.prod.yml:305-333`

**문제**: `deal-mgmt-api`는 `JWT_SECRET: ${SHARED_JWT_SECRET}`를 사용하지만, celery-worker의 prod override에는 `JWT_SECRET`가 없어 dev 기본값(`dev-shared-jwt-secret-change-in-production`)이 적용됨.

**수정**: celery-worker environment에 `JWT_SECRET: ${SHARED_JWT_SECRET}` 추가.

#### [R6-FE-02] `useDecideApproval`/`useCancelApproval` txnId 미스코핑 — [Major/HIGH] — Score: 70

**위치**: `amic-platform/src/modules/ma/hooks/useApprovals.ts:95-130`

**문제**: predicate 기반 invalidation이 모든 거래의 approval 캐시를 무효화함. `txnId`가 없어 스코핑 불가.

**수정**: `txnId` 파라미터 추가 후 prefix invalidation으로 변경.

#### [R6-INFRA-02] CI Python 3.11 vs FDD Dockerfile Python 3.12 불일치 — [Major/HIGH] — Score: 70

**위치**: `.github/workflows/ci.yml:19` vs `fdd/backend/Dockerfile:9`

**문제**: CI는 Python 3.11, FDD Docker는 3.12. 다른 모듈은 3.11 통일.

**수정**: FDD Dockerfile을 `python:3.11-slim-bookworm`으로 변경하거나, CI에서 FDD만 3.12 사용.

#### [R6-INFRA-03] 프로덕션 총 메모리 ~15.5GB → 16GB VM OOM 위험 — [Major/HIGH] — Score: 70

**위치**: `docker-compose.prod.yml` 전체

**문제**: 명시된 메모리 한도 합산 ~15.5GB + 한도 미설정 서비스 + OS 오버헤드 → 16GB VM에서 OOM. 신규 deal-mgmt-redis(512M) + celery-worker(1G) = 1.5GB 추가.

**수정**: deal-mgmt-redis를 256M, celery-worker를 512M으로 축소 검토.

#### [R6-TEST-01] transcription 해피패스 테스트 0건 — [Major/HIGH] — Score: 70

**위치**: `deal-mgmt/tests/test_transcription.py`

**문제**: 6개 테스트 전부 에러 경로. 정상 업로드(audio/mpeg → 202) 테스트 없음.

#### [R6-TEST-02] deal_clients RBAC guard 미테스트 — [Major/HIGH] — Score: 70

**위치**: `deal-mgmt/tests/test_deal_clients.py`

**문제**: `require_role("ADMIN", "MANAGER")` 제한이 있으나, ANALYST/CLIENT 역할 거부 테스트 없음.

---

### P2 — 개선 권장

#### [R6-FE-03] Dead `useUpdateDistribution(id)` call — [Major/MEDIUM] — Score: 42

**위치**: `TransactionWorkspacePage.tsx:556`

**문제**: 반환값을 사용하지 않는 `useUpdateDistribution(id)` 호출. 주석에 "향후 사용 예정" — 불필요한 mutation observer 생성.

#### [R6-SEC-01] `my_pending_approvals` cross-deal 접근 제한 없음 — [Major/MEDIUM] — Score: 42

**위치**: `deal-mgmt/app/routers/approvals.py:225-243`

**문제**: 모든 PENDING approval 200건을 로드 후 Python에서 필터링. `check_client_deal_access` 없음. limit(200) before filter로 본인 approval 누락 가능.

#### [R6-FE-04] `useGenerateRFIFromDD` DD 체크리스트 캐시 cross-invalidation 누락 — [Major/MEDIUM] — Score: 42

**위치**: `amic-platform/src/modules/ma/hooks/useRFI.ts:323-340`

**문제**: `useSyncRFIToChecklists`는 DD 캐시를 무효화하지만, `useGenerateRFIFromDD`는 하지 않음. 백엔드가 DD 항목을 수정하면 stale data 발생.

#### [R6-TEST-03] `test_approvals.py` — body.email != claims.email 보안 시나리오 미테스트 — [Major/MEDIUM] — Score: 42

**위치**: `deal-mgmt/tests/test_approvals.py`

**문제**: `body.email`에 다른 사람 이메일을 넣어도 JWT claims.email 기준으로 동작하는지 검증하는 테스트 없음.

---

## Methodology

- **Agents**: Error/Edge/Security, FE State/Hook/Cache, CI/Infra/Deploy, Test Quality, Architecture/Type
- **Files scanned**: 60개 (49 modified + 11 new)
- **Protocol**: Verified Claim Protocol v1.1
- **Cross-verification**: 3건 교차 확인 (R6-API-01, R6-BLOB-01, R6-KPI-01)
- **Backend availability**: deal-mgmt ✅ | FDD ✅ | KIIS ✅ | IM ✅
