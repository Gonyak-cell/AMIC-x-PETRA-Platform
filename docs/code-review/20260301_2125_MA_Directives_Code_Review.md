# Code Review — MA 6대 핵심 지시사항 구현

> **Review Date**: 2026-03-01 21:25
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 6대 핵심 지시사항 (Long-List 간소화, PEF FI 추천, Short-List 승격, 마케팅 로그 통합, 입찰 결과 추적, 파이프라인 9단계)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) pytest-1031/1031(PASS) vite-build(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(4 에이전트 호출)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1 | HIGH: 1 | P0: 1 |
| Major | 5 | HIGH: 4 / MEDIUM: 1 | P1: 4 / P2: 1 |
| Moderate | 4 | HIGH: 1 / MEDIUM: 3 | P2: 3 / P3: 1 |
| Minor | 3 | MEDIUM: 3 | P3: 3 |
| **Total** | **13** | HIGH: **6** / MEDIUM: **7** | P0: **1** / P1: **4** / P2: **4** / P3: **4** |

**FP Prevention**: 가설 18건 검증, 5건 사전 거부 (거부율: 28%) | 교차 검증 11건 수행

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

---

#### [C-1] Migration 046 — 잘못된 테이블명 + 존재하지 않는 컬럼 — [Critical/HIGH] — Priority: P0

- **위치**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:39,46,56,58,62,65`
- **카테고리**: 안정성(§4) — 데이터 무결성
- **신뢰도**: HIGH (3개 에이전트 독립 발견 + 교차 검증 확인)
- **교차 검증**: CONFIRMED

**근거**:
```python
# migration 046:39 — 잘못된 테이블명
op.execute("UPDATE deal_timelines SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'")
```

```python
# timeline.py:13 — 실제 테이블명은 singular
__tablename__ = "deal_timeline"
```

```python
# timeline.py:19-24 — phase 컬럼이 존재하지 않음
event_type: Mapped[str] = mapped_column(String(50), nullable=False)
title: Mapped[str] = mapped_column(String(200), nullable=False)
description: Mapped[str | None] = mapped_column(Text, nullable=True)
event_date: Mapped[str] = mapped_column(String(10), nullable=False)
```

**문제**:
1. 테이블명 오류: `deal_timelines`(복수) → 실제는 `deal_timeline`(단수)
2. `deal_timeline` 테이블에 `phase` 컬럼 자체가 없음 — event_type, title, description, event_date만 존재
3. PostgreSQL에서는 `relation "deal_timelines" does not exist` 에러로 마이그레이션 실패
4. SQLite에서는 에러 없이 0건 업데이트 (Silent failure)

**영향**: 마이그레이션 실행 시 PostgreSQL에서 런타임 에러. 프로덕션 배포 차단.

**수정 제안**: `deal_timelines` 참조하는 4개 UPDATE 문 전부 제거. `deal_timeline` 테이블에는 phase 컬럼이 없으므로 데이터 마이그레이션 대상이 아님. transactions 테이블의 UPDATE만 유지.

---

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [M-1] usePefRegistry.ts 쿼리 키 불일치 — 캐시 무효화 실패 — [Major/HIGH] — Priority: P1

- **위치**: `amic-platform/src/modules/ma/hooks/usePefRegistry.ts:8,23,46`
- **카테고리**: 완전성(§2) — 통합 완전성
- **신뢰도**: HIGH
- **교차 검증**: CONFIRMED

**근거**:
```typescript
// usePefRegistry.ts:46 — 잘못된 키
queryKey: ["buyers", txnId],  // invalidation target

// useTransactions.ts:319 — 실제 buyer 쿼리 키
queryKey: ["ma", "transactions", txnId, "buyers"],
```

프로젝트 컨벤션 (`useTransactions.ts`):
- `["ma", "transactions", txnId, "buyers"]` — buyer 목록
- `["ma", "transactions", txnId, "buyers", "summary"]` — 요약

usePefRegistry.ts 3개 훅 전부 컨벤션 위반:
- `["fi-recommendations", txnId]` → `["ma", "transactions", txnId, "fi-recommendations"]`
- `["bidding-summary", txnId]` → `["ma", "transactions", txnId, "buyers", "bidding-summary"]`
- `["buyers", txnId]` (invalidation) → `["ma", "transactions", txnId, "buyers"]`

**영향**: Short-List 승격 후 buyer 목록이 자동 갱신되지 않음. 사용자가 수동으로 새로고침해야 변경 확인 가능.

**수정 제안**: 3개 훅의 queryKey를 프로젝트 컨벤션(`["ma", "transactions", txnId, ...]`)으로 통일.

---

#### [M-2] buyer_marketing.py — Short-List 정의 불일치 (tier 기반 → is_short_listed 미전환) — [Major/HIGH] — Priority: P1

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py:246-251`
- **카테고리**: 정합성(§1) — 로직 일관성
- **신뢰도**: HIGH
- **교차 검증**: CONFIRMED

**근거**:
```python
# buyer_marketing.py:246-251 — 여전히 tier 기반
# Short-List = tier IS NOT NULL AND tier != NOT_TARGET
buyers_q = select(BuyerCandidate.id).where(
    BuyerCandidate.transaction_id == txn_id,
    BuyerCandidate.tier.isnot(None),
    BuyerCandidate.tier != BuyerTier.NOT_TARGET,
)
```

6대 지시사항으로 Short-List 기준이 `is_short_listed` 플래그 기반으로 변경되었으나, marketing-stage-summary 엔드포인트는 아직 구 tier 기반 필터를 사용.

**영향**: `/marketing-stage-summary` API 결과와 Short-List UI 탭(is_short_listed 기반)에 표시되는 buyer 목록이 불일치. 마케팅 단계 통계가 부정확.

**수정 제안**: `BuyerCandidate.is_short_listed == True`로 변경.

---

#### [M-3] seed_pef_registry.py — SQL 인젝션 (f-string SQL 구성) — [Major/HIGH] — Priority: P1

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py:103`
- **카테고리**: 안정성(§4) — 보안
- **신뢰도**: HIGH (2개 에이전트 독립 발견)
- **교차 검증**: CONFIRMED

**근거**:
```python
# seed_pef_registry.py:102-110 — pef_name이 escape 없이 직접 삽입
values_list.append(
    f"('{r['id']}', '{r['pef_name']}', "    # ← pef_name 미escape
    f"{_sql_str(r['legal_basis'])}, "         # ← _sql_str()로 escape
    f"{_sql_str(r['registration_date'])}, "   # ← _sql_str()로 escape
    ...
)
```

`_sql_str()` 함수(line 125)로 escape하는 다른 필드와 달리, `pef_name`은 직접 f-string에 삽입. PEF 명칭에 작은따옴표가 포함되면 SQL 구문 오류 또는 인젝션 가능.

**영향**: admin CLI 스크립트이므로 외부 공격 벡터는 아니나, xlsx 데이터에 특수문자가 있으면 시드 실패. 올바른 코딩 관행 위반.

**수정 제안**: `pef_name`도 `_sql_str()` 적용. 또는 전체를 파라미터화된 INSERT로 리팩토링 (`session.execute(text(...), params)`).

---

#### [M-4] FE BuyerCandidateUpdate — is_short_listed 필드 누락 — [Major/HIGH] — Priority: P1

- **위치**: `amic-platform/src/modules/ma/types/buyer.ts:73-91`
- **카테고리**: 정합성(§1) — BE↔FE 계약 불일치
- **신뢰도**: HIGH
- **교차 검증**: CONFIRMED

**근거**:
```typescript
// buyer.ts:73-91 — BuyerCandidateUpdate에 is_short_listed 없음
export interface BuyerCandidateUpdate {
  company_name?: string;
  // ... (18개 필드)
  extra_data?: Record<string, unknown>;
  // is_short_listed 누락!
}
```

BE `BuyerCandidateUpdate` 스키마에는 `is_short_listed: bool | None = None` 존재.
FE에서 type assertion으로 우회: `as BuyerCandidateUpdate & { is_short_listed: boolean }`

**영향**: TypeScript 타입 안전성 손실. 향후 is_short_listed 관련 코드 변경 시 타입 체크가 동작하지 않음.

**수정 제안**: `BuyerCandidateUpdate` 인터페이스에 `is_short_listed?: boolean` 추가. TransactionWorkspacePage의 type assertion 제거.

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [M-5] Short-List 체크박스 — 연락처 검증 우회 경로 — [Major/MEDIUM ⚠️] — Priority: P2

- **위치**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:1858-1866`
- **카테고리**: 안정성(§4) — 비즈니스 규칙 일관성
- **신뢰도**: MEDIUM (설계 의도 불명확)
- **교차 검증**: DESIGN_RISK

⚠️ Major 심각도이나 MEDIUM 신뢰도로 인해 P2로 분류

**근거**: Long-List 체크박스는 generic PATCH(`/buyers/{id}`)를 사용하여 `is_short_listed=true`를 설정. 반면 promote-short-list API는 contact_name/email/phone 필수 검증 수행. 동일 상태 변경에 검증 수준이 다른 두 경로 존재.

**영향**: 연락처 없는 buyer가 체크박스로 Short-List에 올라갈 수 있음.

**수정 제안**: 두 가지 옵션 — (A) 체크박스도 promote API 경유, (B) PATCH 엔드포인트에서 is_short_listed=true 설정 시 연락처 검증 추가.

---

#### [m-1] BUYER_STATUS_VARIANT — BID 3개 상태 누락 — [Moderate/HIGH] — Priority: P2

- **위치**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:352-370`
- **카테고리**: 완전성(§2) — UI 완전성
- **신뢰도**: HIGH
- **교차 검증**: CONFIRMED

**근거**:
```typescript
const BUYER_STATUS_VARIANT: Record<string, ...> = {
  IDENTIFIED: "neutral",
  // ... 14개 상태만 매핑
  REJECTED: "error",
  // BID_SUBMITTED, BID_NOT_SUBMITTED, BID_DROPPED 누락
};
```

**영향**: BID 상태의 buyer Badge가 기본 스타일로 렌더링. 시각적 구분 부재.

**수정 제안**: `BID_SUBMITTED: "success"`, `BID_NOT_SUBMITTED: "warning"`, `BID_DROPPED: "error"` 추가.

---

#### [m-2] Migration 046 — COMMIT 패턴 개선 필요 — [Moderate/MEDIUM] — Priority: P2

- **위치**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:32`
- **카테고리**: 안정성(§4) — 마이그레이션 안전성
- **신뢰도**: MEDIUM
- **교차 검증**: PARTIAL

**근거**: `op.execute("COMMIT")`은 PostgreSQL `ALTER TYPE ADD VALUE`에 필요하지만, 이후 DML 실패 시 롤백 불가. `IF NOT EXISTS`로 멱등성은 보장되나, 마이그레이션이 부분 적용 상태로 남을 수 있음.

**영향**: 마이그레이션 실패 시 수동 복구 필요 가능.

**수정 제안**: Alembic `autocommit` 블록 패턴 또는 별도 마이그레이션 파일로 분리.

---

#### [m-3] Migration 045 — server_default=sa.text("0") 비관용적 — [Moderate/MEDIUM] — Priority: P2

- **위치**: `deal-mgmt/migrations/versions/045_ma_directives_phase1.py:58`
- **카테고리**: 정합성(§1) — DB 컨벤션
- **신뢰도**: MEDIUM
- **교차 검증**: PARTIAL

**근거**: Boolean 컬럼의 기본값으로 `sa.text("0")` 사용. PostgreSQL에서 `0`은 `false`로 암묵 변환되어 동작하지만, `sa.text("false")` 또는 `sa.false_()`가 관용적.

**영향**: 기능적 문제 없음. 코드 가독성 및 의도 명확성 개선 가능.

---

### P3 — 저우선 (점수: <30)

---

#### [m-4] useBiddingSummary — 정의만 존재, UI에서 미사용 — [Moderate/MEDIUM] — Priority: P3

- **위치**: `amic-platform/src/modules/ma/hooks/usePefRegistry.ts:20-32`
- **카테고리**: 완전성(§2) — Dead code
- **신뢰도**: MEDIUM

**근거**: `useBiddingSummary` 훅이 정의되었으나 어떤 컴포넌트에서도 import/사용되지 않음. 계획서의 "Short-List 하단에 BiddingSummary 카드 3개" 미구현 가능성.

**영향**: 기능 누락 (입찰 집계 UI 미표시). 또는 향후 사용 예정 코드.

---

#### [L-1] FIRecommendModal — 에러 상태 미처리 — [Minor/MEDIUM] — Priority: P3

- **위치**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:86-98`
- **카테고리**: 품질(§3) — 에러 처리
- **신뢰도**: MEDIUM

**근거**: isLoading과 empty 상태만 처리. `isError` 상태에 대한 UI 미구현. API 실패 시 빈 모달 표시.

---

#### [L-2] ShortListPromoteRequest — buyer_ids 크기 제한 없음 — [Minor/MEDIUM] — Priority: P3

- **위치**: `deal-mgmt/app/schemas/buyer.py` (ShortListPromoteRequest)
- **카테고리**: 안정성(§4) — 입력 검증
- **신뢰도**: MEDIUM

**근거**: `buyer_ids: list[uuid.UUID]` 에 max_length 미설정. 극단적 경우 수천 개 UUID로 DB 부하.

---

#### [L-3] test_workflow.py docstring — "7단계" 표기 미수정 — [Minor/MEDIUM] — Priority: P3

- **위치**: `deal-mgmt/tests/test_workflow.py` (docstring)
- **카테고리**: 정합성(§1) — 문서 일관성
- **신뢰도**: MEDIUM

**근거**: 9단계로 변경되었으나 테스트 파일 docstring이 "7단계"로 남아있을 수 있음.

---

## §6 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | Long-List에서 Status/IOI/LOI 컬럼 제거 | ✅ | TransactionWorkspacePage — buyerColumns에서 제거 확인 |
| 2 | PEF 레지스트리 모델 + 시드 + FI 자동 추천 | ✅ | pef_fund_registry.py, seed_pef_registry.py, pef_registry.py 라우터 확인 |
| 3 | Short-List 승격 + 연락처 필수 검증 | ✅ | buyers.py:134-195 promote-short-list 엔드포인트 확인 |
| 4 | is_short_listed 플래그 기반 Short-List | ⚠️ | buyer_candidate.py + FE 확인. **단, buyer_marketing.py가 아직 tier 기반** [M-2] |
| 5 | 입찰 결과 추적 (BID 3개 상태) | ✅ | enums.py에 3개 상태 추가, bidding-summary API 확인 |
| 6 | 파이프라인 7→9단계 재구성 | ⚠️ | enums.py 9단계 확인. **단, Migration 046에 잘못된 테이블 참조** [C-1] |
| 7 | FIRecommendModal 프론트엔드 | ✅ | FIRecommendModal.tsx 170줄 구현 확인 |
| 8 | usePefRegistry 훅 3개 | ⚠️ | 구현 확인. **단, queryKey 컨벤션 불일치** [M-1] |
| 9 | BuyerCandidateUpdate에 is_short_listed | ⚠️ | BE 확인. **FE 타입 누락** [M-4] |
| 10 | BUYER_STATUS_VARIANT BID 상태 매핑 | ⚠️ | **3개 BID 상태 누락** [m-1] |
| 11 | Short-List ↔ 마케팅 로그 통합 | ✅ | ShortListOverview.tsx — is_short_listed 필터 확인 |
| 12 | BiddingSummary UI 카드 | ❌ | useBiddingSummary 훅 정의됨, **UI에서 미사용** [m-4] |

**구현율**: 7/12 완전 구현 (58%), 4/12 부분 구현, 1/12 누락

---

## §7 품질 게이트 상태

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| ruff check | ✅ PASS | §1 린트 자동 검증됨 |
| ruff format | ✅ PASS | §1 포맷 자동 검증됨 |
| tsc --noEmit | ✅ PASS | §3 타입 에러 없음 자동 검증됨 |
| vite build | ✅ PASS | §2 빌드 성공 자동 검증됨 |
| pytest (1031/1031) | ✅ PASS | §2 테스트 자동 검증됨 |

---

## Cross-Verification Results

| Issue | Phase 1 | Phase 2 판정 | 변경 |
|-------|---------|------------|------|
| [C-1] Migration 046 테이블명 | Critical/HIGH (3개 에이전트) | CONFIRMED | 유지 |
| [M-1] Query key 불일치 | Major/HIGH (2개 에이전트) | CONFIRMED | 유지 |
| [M-2] buyer_marketing tier 기반 | Major/HIGH | CONFIRMED | 유지 |
| [M-3] SQL 인젝션 | Critical/HIGH (2개 에이전트) | CONFIRMED → Major/HIGH | 심각도 하향 (CLI 스크립트) |
| [M-4] FE is_short_listed 누락 | Critical/HIGH | CONFIRMED → Major/HIGH | 심각도 하향 (타입 안전성만) |
| [M-5] 체크박스 검증 우회 | Major/HIGH | DESIGN_RISK → Major/MEDIUM | 신뢰도 하향 |
| UUID(as_uuid=True) | Major/HIGH | FALSE_POSITIVE (FP-CTX) | 제거 — 기존 패턴 |
| PEF Registry main.py 누락 | Moderate/HIGH | FALSE_POSITIVE | 제거 — main.py:203에 등록됨 |
| float vs Decimal | Major/MEDIUM | PARTIAL → Moderate/MEDIUM | 심각도 하향 — 기존 코드 |
| estimated_deal_value 타입 | Major/MEDIUM | FALSE_POSITIVE (FP-CTX) | 제거 — 런타임 정상 |
| AUTH_ENABLED bypass | Medium/HIGH | FALSE_POSITIVE | 제거 — 프로덕션 가드 존재 |

---

## Priority Matrix

### P0 — 즉시 수정 (1건)
1. [C-1] [Critical/HIGH]: Migration 046 잘못된 테이블명 + 존재하지 않는 컬럼 — `046_transaction_phase_restructure.py` (점수: 100)

### P1 — 스프린트 우선 (4건)
1. [M-1] [Major/HIGH]: usePefRegistry 쿼리 키 컨벤션 불일치 — `usePefRegistry.ts` (점수: 70)
2. [M-2] [Major/HIGH]: buyer_marketing Short-List 정의 불일치 — `buyer_marketing.py` (점수: 70)
3. [M-3] [Major/HIGH]: seed_pef_registry SQL 인젝션 — `seed_pef_registry.py` (점수: 70)
4. [M-4] [Major/HIGH]: FE BuyerCandidateUpdate is_short_listed 누락 — `buyer.ts` (점수: 70)

### P2 — 개선 권장 (4건)
1. [M-5] [Major/MEDIUM ⚠️]: Short-List 체크박스 검증 우회 — `TransactionWorkspacePage.tsx` (점수: 42)
2. [m-1] [Moderate/HIGH]: BUYER_STATUS_VARIANT BID 3상태 누락 — `TransactionWorkspacePage.tsx` (점수: 40)
3. [m-2] [Moderate/MEDIUM]: Migration 046 COMMIT 패턴 — `046_transaction_phase_restructure.py` (점수: 24)
4. [m-3] [Moderate/MEDIUM]: Migration 045 server_default 비관용적 — `045_ma_directives_phase1.py` (점수: 24)

### P3 — 저우선 (4건)
1. [m-4] [Moderate/MEDIUM]: useBiddingSummary 미사용 — `usePefRegistry.ts` (점수: 24)
2. [L-1] [Minor/MEDIUM]: FIRecommendModal 에러 상태 미처리 — `FIRecommendModal.tsx` (점수: 12)
3. [L-2] [Minor/MEDIUM]: ShortListPromoteRequest 크기 제한 없음 — `buyer.py` (점수: 12)
4. [L-3] [Minor/MEDIUM]: test_workflow docstring 7단계→9단계 미수정 — `test_workflow.py` (점수: 12)

---

## Methodology

- **Agents**: python-code-reviewer, general-purpose (frontend), migration-validator, backend-security-reviewer
- **Excluded Agents**: a11y-auditor (프론트엔드 컴포넌트 변경 범위 제한)
- **Files scanned**: ~30개 (BE 모델/라우터/서비스/마이그레이션/테스트 + FE 타입/훅/컴포넌트/페이지)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 11건 수행 → 5건 FP 제거, 2건 심각도 조정

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 18건
- 거부된 가설 (사전 제거): 5건
- 보고된 이슈: 13건
- 거부율: 28%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 (FP-CTX) | 3 | UUID(as_uuid=True) 기존 패턴, AUTH_ENABLED 프로덕션 가드 존재 |
| 범위 외 | 1 | estimated_deal_value float 타입 — 기존 코드, 런타임 정상 |
| 중복 | 1 | PEF Registry main.py 등록 — 실제 등록 확인됨 |
