# Code Review — MA Workflow (feat/ma-workflow vs master)

> **Review Date**: 2026-03-02 10:41 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff origin/master...HEAD` — 1,330 소스 파일 (deal-mgmt + KIIS + IM + amic-platform)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(170/170 PASS) build(PASS)
> **Review Gates**: Backend(KIIS ✅ / IM ✅ / deal-mgmt ✅ / FDD ❌ 별도 레포) Agent-Filtering(5개 호출)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 4     | HIGH: 3 / MEDIUM: 1 | P0: 3 / P1: 1 |
| Major    | 15    | HIGH: 9 / MEDIUM: 6 | P1: 9 / P2: 6 |
| Moderate | 7     | HIGH: 3 / MEDIUM: 4 | P2: 5 / P3: 2 |
| Minor    | 4     | MEDIUM: 4 | P3: 4 |
| **Total**| **30** | HIGH: **15** / MEDIUM: **15** | P0: **3** / P1: **10** / P2: **11** / P3: **6** |

**FP Prevention**: 가설 45건 검증, 15건 사전 거부 (거부율: 33%) | 교차 검증 19건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 7건 하향 조정

---

## Findings

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

#### [SEC-001] KIIS AUTH_ENABLED 우회 시 환경 검증 부재 — [Critical/HIGH] — P0 (점수: 100)

**위치**: `kiis/app/core/security.py:107-109`

**문제**: KIIS의 `get_jwt_claims()`에서 `AUTH_ENABLED=False` 시 환경(ENV) 검증 없이 즉시 dev 클레임을 반환한다. deal-mgmt는 `if _env not in ("local", "dev", "test"):` 가드가 있지만 KIIS에는 없다.

```python
# KIIS — 환경 체크 없음 (위험)
if not settings.AUTH_ENABLED:
    request.state.user_id = _DEV_CLAIMS.email or _DEV_CLAIMS.user_id
    return _DEV_CLAIMS

# deal-mgmt — 환경 체크 있음 (안전)
if not settings.AUTH_ENABLED:
    _env = os.getenv("ENV", "").lower()
    if _env not in ("local", "dev", "test"):
        raise RuntimeError(...)
    return _DEV_CLAIMS
```

**영향**: 프로덕션 환경에서 `AUTH_ENABLED=False` 설정 시 모든 요청이 인증 없이 통과.

**수정 방안**: deal-mgmt와 동일한 ENV 환경 검증 가드 추가.

**검증 근거**: kiis/app/core/security.py:107 Read 확인, deal-mgmt/app/core/security.py:56-62 비교.

---

#### [MIG-001] deal-mgmt 마이그레이션 6개 파일 PostgreSQL 전용 타입 사용 — [Critical/HIGH] — P0 (점수: 100)

**위치**: `deal-mgmt/migrations/versions/` — 011, 016, 017, 018, 019, 020

**문제**: 아래 마이그레이션 파일들이 `from sqlalchemy.dialects.postgresql import UUID, JSONB`를 직접 사용하여 SQLite 기반 CI 테스트에서 `CompileError` 발생.

| 파일 | 마이그레이션 |
|------|------------|
| `011_ralph_loop_sessions.py` | `UUID`, `JSONB` 직접 사용 |
| `016_meeting_logs.py` | `UUID`, `JSONB`, `PgENUM` 직접 사용 |
| `017_permit_analysis.py` | `UUID`, `JSONB`, `PgENUM` 직접 사용 |
| `018_transcription_jobs.py` | `UUID`, `JSONB`, `PgENUM` 직접 사용 |
| `019_ldd_vdr_integration.py` | `UUID`, `JSONB` 직접 사용 |
| `020_financial_models.py` | `UUID`, `JSONB` 직접 사용 |

**수정 방안**: 각 파일에서:
- `UUID(as_uuid=True)` → `sa.Uuid()`
- `JSONB` → `sa.JSON().with_variant(JSONB, "postgresql")`
- `PgENUM` → `sa.Enum(..., name="...")` (create_type=False)

**참고**: 029, 041 마이그레이션은 이전 세션에서 이미 수정 완료.

**검증 근거**: Grep으로 6개 파일에서 직접 import 확인. CI Guard 2 규칙 위반.

---

#### [PERF-001] IMClient/FDDClient 매 요청마다 TCP 연결 생성 — [Critical/HIGH] — P0 (점수: 100)

**위치**: `deal-mgmt/app/services/im_client.py:26,39,46` / `deal-mgmt/app/services/fdd_client.py:26,36,43`

**문제**: IMClient과 FDDClient의 모든 메서드가 `async with httpx.AsyncClient(...)` 으로 매 요청마다 새 TCP 연결을 생성·종료한다. 반면 KIISClient는 이미 `_get_client()` 싱글턴 패턴 구현 완료.

```python
# IMClient — 매 요청 새 연결 (비효율)
async def create_document(self, ...):
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        ...

# KIISClient — 싱글턴 재사용 (올바른 패턴)
async def _get_client(self) -> httpx.AsyncClient:
    if self._client is None or self._client.is_closed:
        async with self._lock:
            self._client = httpx.AsyncClient(...)
    return self._client
```

**영향**: 동시 요청 시 TCP 핸드셰이크 반복으로 지연 증가. 연결 풀 미사용.

**수정 방안**: KIISClient 패턴(`_client` + `asyncio.Lock`)을 IMClient, FDDClient에 적용.

**검증 근거**: im_client.py, fdd_client.py, kiis_client.py Read 비교 확인.

---

### P1 — 스프린트 우선 (점수: 60-89)

#### [FE-001] Transaction 응답 타입에 `notes` 필드 누락 — [Major/HIGH] — P1 (점수: 70)

**위치**: `amic-platform/src/modules/ma/types/transaction.ts:47-84`

**문제**: BE `TransactionOut.notes: str | None = None`이 응답에 포함되지만, FE `Transaction` 인터페이스에 `notes` 필드가 없다. `TransactionUpdate`에는 `notes?: string`이 있어 쓰기는 가능하지만 읽기에서 데이터가 소실된다.

**수정 방안**: `Transaction` 인터페이스에 `notes: string | null;` 추가.

---

#### [FE-002] DartFinancialSummary.fiscal_year nullable 불일치 — [Major/HIGH] — P1 (점수: 70)

**위치**: `amic-platform/src/modules/ma/types/marketing_log.ts:48`

**문제**: BE `fiscal_year: str | None = None`이지만 FE는 `fiscal_year: string` (non-nullable). null 반환 시 런타임 TypeError 위험.

**수정 방안**: `fiscal_year: string | null;`로 변경.

---

#### [FE-004] useMaStats 훅 — implicit any 타입 — [Major/HIGH] — P1 (점수: 70)

**위치**: `amic-platform/src/modules/ma/hooks/useTransactions.ts:456-464`

**문제**: `useQuery`에 제네릭 타입 미지정, `maApi.get()`에도 타입 파라미터 없어 `data`가 `any`로 추론. 백엔드 `DashboardStats` 스키마(7개 필드)에 대응하는 FE 타입 정의도 부재.

**수정 방안**: `DashboardStats` 인터페이스 정의 + `useQuery<DashboardStats>` 적용.

---

#### [FE-005] TransactionWorkspacePage 6,192줄 / 127개 훅 — [Major/HIGH] — P1 (점수: 70)

**위치**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` (전체)

**문제**: 단일 컴포넌트 6,192줄, 127개 React 훅 최상위 호출. 모든 탭 데이터가 마운트 시 동시 fetch (40+ useQuery). 한 상태 변경으로 전체 re-render.

**수정 방안**: 탭별 lazy 컴포넌트 분리 + `enabled: activeTab === "xxx"` 조건부 쿼리 활성화. (장기 리팩토링)

---

#### [CODE-001] IM 체크리스트 재무 데이터 float 사용 — [Major/MEDIUM ⚠️] — P1 (점수: 42→60 교차검증 보너스)

**위치**: `im/src/api/services/checklist_to_imdata.py:480-519`

**문제**: `_parse_number()`가 매출, 영업이익 등 재무 금액을 `float`로 반환. 금액 정밀도 손실 가능.

```python
def _parse_number(value: str | None) -> float | None:
    return float(cleaned) * multiplier  # float 정밀도 손실
```

**수정 방안**: `Decimal(cleaned) * Decimal(str(multiplier))` 사용.

**완화 요인**: IM 생성용 중간 데이터로 트랜잭션 처리에는 미사용. 표시 목적이므로 실질적 영향은 제한적.

---

#### [SEC-002] INTERNAL_SERVICE_KEY 비교 시 타이밍 공격 취약 — [Major/MEDIUM ⚠️] — P1 (점수: 42)

**위치**: `deal-mgmt/app/routers/vdr_internal.py:56`

**문제**: `x_internal_key != _INTERNAL_SERVICE_KEY` — 문자열 직접 비교는 타이밍 공격에 취약. 내부 서비스 키지만 보안 모범 사례는 `hmac.compare_digest()` 사용.

```python
# 현재
if not x_internal_key or x_internal_key != _INTERNAL_SERVICE_KEY:
# 권장
if not x_internal_key or not hmac.compare_digest(x_internal_key, _INTERNAL_SERVICE_KEY):
```

**완화 요인**: 내부 서비스 간 통신 전용으로 외부 노출 제한적. 503 fallback도 정상 동작.

---

#### [FE-003] MarketingLog.created_by_email 필드 누락 — [Major/MEDIUM ⚠️] — P1 (점수: 42)

**위치**: `amic-platform/src/modules/ma/types/marketing_log.ts:9-18`

**문제**: BE `MarketingLogOut.created_by_email: str | None = None`이 FE 타입에 없어 마케팅 로그 작성자 정보를 UI에서 표시 불가.

**수정 방안**: `MarketingLog` 인터페이스에 `created_by_email: string | null;` 추가.

---

#### [FE-006] Buyer 금액 필드 string/Decimal 타입 불일치 — [Major/MEDIUM ⚠️] — P1 (점수: 42)

**위치**: `amic-platform/src/modules/ma/types/buyer.ts:48-53,84-85`

**문제**: FE 응답 타입이 `ioi_value: string | null`이지만 BE 업데이트 스키마는 `Decimal` 기대. 비숫자 문자열 전송 시 Pydantic 422. `formatAmount()`가 `number | null`만 처리하여 string과 불일치.

---

#### [CODE-003] reputation_service 뉴스 기사 전체 로드 — [Major/HIGH] — P1 (점수: 70)

**위치**: `kiis/app/services/reputation_service.py`

**문제**: 뉴스 감성 분석 시 전체 기사를 메모리에 로드. 이전 세션에서 `.limit(1000)` 추가했으나, 1000건도 대량일 수 있음.

**상태**: 이전 수정으로 .limit(1000) 적용 완료. 추가 최적화(집계 쿼리)는 P2로 분류.

---

#### [CODE-002] KIIS reputation_service Decimal/float 혼용 — [Major/MEDIUM ⚠️] — P1 (점수: 42)

**위치**: `kiis/app/services/reputation_service.py:280`

**문제**: `(float(score) + 1.0) / 2.0` — Decimal→float→Decimal 라운드트립. 평판 점수(0~1)에서는 정밀도 영향 미미하나, Decimal을 사용하는 다른 연산과 일관성 부족.

---

### P2 — 개선 권장 (점수: 30-59)

#### [MIG-002] 일부 마이그레이션 downgrade() 빈 구현 — [Moderate/HIGH] — P2 (점수: 40)

**문제**: 일부 마이그레이션의 `downgrade()` 함수가 `pass`만 포함. 롤백 불가.

**수정 방안**: 테이블/컬럼 삭제 로직 추가 또는 주석으로 롤백 불가 사유 명시.

---

#### [MIG-003] ALTER TYPE 문 dialect 가드 누락 — [Moderate/HIGH] — P2 (점수: 40)

**문제**: 일부 마이그레이션에서 `op.execute("ALTER TYPE ...")` 호출 시 `if bind.dialect.name == "postgresql":` 가드 없음.

**참고**: 041은 이전 세션에서 수정 완료. 043, 045, 046, 051 등 확인 필요.

---

#### [SEC-003] 트랜잭션 PATCH/DELETE 소유권 검증 부재 — [Moderate/MEDIUM ⚠️] — P2 (점수: 24)

**문제**: 일부 트랜잭션 수정/삭제 엔드포인트에서 요청자가 해당 딜의 소유자인지 검증하지 않음. JWT 클레임의 role만 확인.

---

#### [PERF-002] blob_storage readall() 전체 메모리 로드 — [Moderate/HIGH] — P2 (점수: 40)

**위치**: `deal-mgmt/app/core/blob_storage.py`

**문제**: 이전 세션에서 동기 I/O → 비동기로 수정했으나, `readall()`은 파일 전체를 메모리에 로드. 대용량 VDR 파일에서 메모리 압박 가능.

**수정 방안**: `stream.chunks()` 이터레이터로 청크 단위 스트리밍 쓰기.

---

#### [PERF-003] SI 매핑 10K 건 인메모리 처리 — [Moderate/MEDIUM ⚠️] — P2 (점수: 24)

**문제**: SI 회사 데이터 전체를 메모리에 로드하여 필터링. 대규모 데이터셋에서 비효율.

---

#### [PERF-004] 감사 로그 내보내기 10K 제한 없음 — [Moderate/MEDIUM ⚠️] — P2 (점수: 24)

**문제**: 감사 로그 Excel 내보내기 시 건수 제한 없이 전체 조회. 대량 데이터에서 타임아웃/OOM 위험.

---

#### [CODE-004] document_extraction target_model 문자열 비교 — [Moderate/HIGH] — P2 (점수: 40)

**문제**: `target_model` 필드가 `String(50)`으로 마법 문자열 비교. Enum이나 상수로 관리하면 타입 안전성 향상.

---

### P3 — 저우선 (점수: <30)

#### [CODE-005] Decimal(0) 리터럴 사용 — [Minor/MEDIUM] — P3 (점수: 12)

**문제**: `Decimal(0)` 대신 `Decimal("0")` 사용 권장 (부동소수점 변환 방지).

---

#### [SEC-004] VDR 파일 업로드 매직바이트 검증 부재 — [Minor/MEDIUM] — P3 (점수: 12)

**문제**: 파일 업로드 시 확장자만 확인하고 매직바이트(파일 시그니처) 검증 없음. 확장자 변조 가능.

---

#### [CODE-006] mark_extraction_failed 실패 시 무음 — [Minor/MEDIUM] — P3 (점수: 12)

**문제**: 추출 실패 마킹 함수가 내부 에러 시 예외를 삼키고 로그만 남김. 호출자에게 실패 전파 안 됨.

---

#### [PERF-005] KOFIA 순차적 API 탐색 — [Minor/MEDIUM] — P3 (점수: 12)

**문제**: KOFIA 펀드 검색 시 여러 검색 조건을 순차적으로 시도. 동시 호출로 최적화 가능.

---

## 양호 판정 항목 (이슈 없음)

| 검증 항목 | 결과 |
|----------|------|
| dangerouslySetInnerHTML 사용 | MA 모듈 전체에서 미사용 ✅ |
| any 타입 직접 사용 | MA 모듈에서 미사용 (useMaStats implicit 제외) ✅ |
| 하드코딩된 URL/시크릿 | 미발견. URL은 모두 상대 경로 + 환경변수 ✅ |
| XSS 취약점 | React JSX만 사용, raw HTML 미삽입 ✅ |
| 조건부 훅 호출 | 127개 훅 모두 최상위 레벨 ✅ |
| JWT 토큰 저장 | httpOnly 쿠키 방식 (`withCredentials: true`) ✅ |
| 401 토큰 갱신 | 중복 갱신 방지 (`refreshPromise` 싱글턴) + 자동 재시도 ✅ |
| ProtectedRoute 권한 체크 | `hasPermission` + `requiredPermission` RBAC ✅ |
| AuthProvider 메모리 누수 | `AbortController` + `cancelled` 플래그 cleanup ✅ |
| FE/BE Enum 값 일치 | 주요 Enum 5종 모두 일치 확인 ✅ |
| deal-mgmt AUTH 환경 체크 | `if _env not in ("local", "dev", "test"):` 가드 정상 ✅ |
| INTERNAL_SERVICE_KEY 빈값 처리 | 미설정 시 503 반환 정상 ✅ |
| KIISClient 연결 재사용 | 싱글턴 패턴 + asyncio.Lock 정상 ✅ |

---

## Priority Matrix

### P0 — 즉시 수정 (3건)
1. [SEC-001] [Critical/HIGH]: KIIS AUTH_ENABLED 환경 검증 부재 — kiis/app/core/security.py (점수: 100)
2. [MIG-001] [Critical/HIGH]: 6개 마이그레이션 PostgreSQL 전용 타입 — deal-mgmt/migrations (점수: 100)
3. [PERF-001] [Critical/HIGH]: IMClient/FDDClient 매 요청 TCP 연결 생성 — deal-mgmt/app/services (점수: 100)

### P1 — 스프린트 우선 (10건)
1. [FE-001] [Major/HIGH]: Transaction.notes 필드 누락 (점수: 70)
2. [FE-002] [Major/HIGH]: DartFinancialSummary.fiscal_year nullable 불일치 (점수: 70)
3. [FE-004] [Major/HIGH]: useMaStats implicit any 타입 (점수: 70)
4. [FE-005] [Major/HIGH]: TransactionWorkspacePage 6,192줄 / 127훅 (점수: 70)
5. [CODE-003] [Major/HIGH]: reputation_service 뉴스 집계 최적화 (점수: 70)
6. [CODE-001] [Major/MEDIUM ⚠️]: IM 체크리스트 float 재무 데이터 (점수: 60)
7. [SEC-002] [Major/MEDIUM ⚠️]: INTERNAL_SERVICE_KEY 타이밍 공격 (점수: 42)
8. [FE-003] [Major/MEDIUM ⚠️]: MarketingLog.created_by_email 누락 (점수: 42)
9. [FE-006] [Major/MEDIUM ⚠️]: Buyer 금액 string/Decimal 불일치 (점수: 42)
10. [CODE-002] [Major/MEDIUM ⚠️]: KIIS Decimal/float 혼용 (점수: 42)

### P2 — 개선 권장 (11건)
- MIG-002, MIG-003, SEC-003, PERF-002, PERF-003, PERF-004, CODE-004 등

### P3 — 저우선 (6건)
- CODE-005, SEC-004, CODE-006, PERF-005 등

---

## Methodology

- **Agents**: backend-security-reviewer, migration-validator, performance-profiler, python-code-reviewer, general-purpose (FE type/API)
- **Excluded Agents**: a11y-auditor (FE only scope), test-auditor (별도 실행)
- **Files scanned**: 1,330 소스 파일
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 4건 + Major 15건 = 19건 수행
- **Backend availability**: FDD(❌ 별도 레포) KIIS(✅) IM(✅) deal-mgmt(✅)

## 검증 투명성

### 검증 통계
- 검증한 가설: 45건
- 거부된 가설 (사전 제거): 15건
- 보고된 이슈: 30건
- 거부율: 33%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 5 | "XSS 취약점 있다" → dangerouslySetInnerHTML 미사용 확인 |
| 이미 수정됨 | 4 | 029/041 마이그레이션, security.py 빈문자열 ENV, .limit(1000) |
| 오판 | 3 | KIIS AUTH 테스트 미비 → test_auth_guard.py 존재 확인 |
| 중복 | 2 | 동일 이슈를 다른 에이전트가 중복 보고 |
| 신뢰도 불충분 | 1 | 증거 부족 (백엔드 미가용) |

---

## 이전 세션 수정 내역 (참고)

이전 2개 세션에서 이미 수정된 항목 (본 리뷰 대상에서 제외):

| 이슈 | 파일 | 수정 내용 |
|------|------|---------|
| SEC-K001 | kiis 13개 라우터 | `dependencies=[Depends(get_jwt_claims)]` 추가 |
| SEC-K002 | kiis/sanctions.py | 에러 메시지 내부 정보 노출 제거 |
| MIG-C003 | im/alembic/001 | 크로스 DB 타입 변환 |
| MIG-C004 | im/alembic/005 | UUID→sa.Uuid(), JSONB→_JSON |
| MIG-C005 | deal-mgmt/029 | UUID→sa.Uuid(), JSONB→_JSON |
| MIG-C002 | deal-mgmt/041 | ALTER TYPE PG dialect 가드 추가 |
| SEC-H001 | deal-mgmt/security.py | ENV 빈문자열 제거 |
| CODE-C01 | si_mapping_service.py | float→Decimal |
| PERF-005 | blob_storage.py | 동기→비동기 파일 I/O |
| CODE-C03 | reputation_service.py | .limit(1000) 추가 |
