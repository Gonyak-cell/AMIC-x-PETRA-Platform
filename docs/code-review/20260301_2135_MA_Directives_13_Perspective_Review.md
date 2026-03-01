# Code Review — MA 6대 핵심 지시사항 (13개 관점 통합)

> **Review Date**: 2026-03-01 21:35
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 6대 핵심 지시사항 구현 전체 (deal-mgmt + amic-platform)
> **Method**: R1 기본 체크리스트 + R2~R6 13개 관점 순차 적용 + 교차 검증
> **Agents**: backend-security-reviewer(R2), migration-validator(R3), performance-profiler(R5), python-code-reviewer(R6), Explore(R4), Direct(R6-UX)

---

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|-----------|----------|
| Critical | 3 | HIGH: 3 | P0: 3 |
| Major | 10 | HIGH: 10 | P1: 10 |
| Moderate | 10 | HIGH: 8 / MEDIUM: 2 | P2: 10 |
| Minor | 8 | HIGH: 6 / MEDIUM: 2 | P3: 8 |
| **Total** | **31** | HIGH: **27** / MEDIUM: **4** | P0: **3** / P1: **10** / P2: **10** / P3: **8** |

**교차 검증**: 48건 이슈 발견 → 17건 중복 병합 → 31건 최종
**FP 방지**: 가설 46건 검증, 10건 사전 거부 (거부율: 22%)

---

## P0 — 즉시 수정 (3건)

### [P0-1] Migration 046: `deal_timelines` 테이블 오타 + `phase` 컬럼 부재 — Critical/HIGH (110점)

- **위치**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:38,46,56,64`
- **교차 검증**: R1 + R3 + R5 (3개 에이전트 확인)
- **관점**: R3 데이터 무결성 + R5 배포 안전성

**문제**: 실제 테이블명은 `deal_timeline`(단수)인데 마이그레이션에서 `deal_timelines`(복수) 참조. 또한 `deal_timeline` 테이블에는 `phase` 컬럼 자체가 존재하지 않음 (`event_type`, `title`, `description`, `event_date`만 존재).

```python
# 046:38 — 존재하지 않는 테이블 + 존재하지 않는 컬럼
op.execute("UPDATE deal_timelines SET phase = 'BIDDING' WHERE phase = 'BIDDING_DD'")
```

```python
# timeline.py:13 — 실제 모델
class DealTimeline(Base, TimestampMixin):
    __tablename__ = "deal_timeline"  # 단수
    # phase 컬럼 없음
```

**영향**: PostgreSQL에서 `relation "deal_timelines" does not exist` 에러 → COMMIT 이후이므로 enum 추가는 롤백 불가 → 반쪽 마이그레이션 상태.

**수정**: upgrade/downgrade 4곳에서 `deal_timelines` 관련 SQL 전체 제거 (테이블에 phase 컬럼이 없으므로 마이그레이션 불필요).

---

### [P0-2] SQL Injection — seed_pef_registry.py `pef_name` f-string — Critical/HIGH (110점)

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py:101-116`
- **교차 검증**: R1 + R2 + R6 (3개 에이전트 확인)
- **관점**: R2 보안 + R6 코드 품질

**문제**: `pef_name`만 `_sql_str()` 이스케이프 없이 f-string으로 직접 SQL 조립.

```python
# seed_pef_registry.py:101
values_list.append(
    f"('{r['id']}', '{r['pef_name']}', "    # pef_name NOT escaped!
    f"{_sql_str(r['legal_basis'])}, "         # 다른 필드는 _sql_str 사용
)
```

**수정**: SQLAlchemy `insert()` + 파라미터 바인딩으로 교체.

---

### [P0-3] `BuyerCandidateUpdate` FE 타입에 `is_short_listed` 누락 — Critical/HIGH (110점)

- **위치**: `amic-platform/src/modules/ma/types/buyer.ts:73-91`
- **교차 검증**: R1 + R3 (2개 에이전트 확인)
- **관점**: R3 API 계약

**문제**: BE `BuyerCandidateUpdate`에는 `is_short_listed: bool | None = None`(buyer.py:62) 존재하나 FE 타입에 없음. `TransactionWorkspacePage.tsx:1852`에서 `as BuyerCandidateUpdate & { is_short_listed: boolean }` 타입 단언으로 강제 우회 중.

```typescript
// buyer.ts — is_short_listed 누락
export interface BuyerCandidateUpdate {
  company_name?: string;
  // ... 16개 필드 — is_short_listed 없음
}
```

**수정**: `is_short_listed?: boolean;` 추가 후 타입 단언 제거.

---

## P1 — 스프린트 우선 (10건)

### [P1-1] `usePefRegistry` 쿼리 키 불일치 + `onError` 누락 — Major/HIGH (80점)

- **위치**: `amic-platform/src/modules/ma/hooks/usePefRegistry.ts:7-8,22-23,44-47`
- **교차 검증**: R1 + R3 + R5 (3개 에이전트 확인)
- **관점**: R3 API 계약 + R5 의존성

**문제**:
1. 쿼리 키가 프로젝트 컨벤션(`["ma", "transactions", txnId, ...]`) 위반 → `["fi-recommendations", txnId]`, `["bidding-summary", txnId]` 사용
2. `onSuccess` 무효화 키 `["buyers", txnId]` → 실제 키 `["ma", "transactions", txnId, "buyers"]`와 불일치 → **무효화 미동작**
3. `onError` 핸들러 완전 누락 → 422 연락처 누락 에러 시 사용자 피드백 없음 (silent failure)

**수정**: 3개 쿼리 키 모두 `["ma", "transactions", txnId, ...]` 패턴으로 통일 + `onError` 추가.

---

### [P1-2] `buyer_marketing.py` Short-List 정의가 tier 기반 — `is_short_listed` 플래그와 이중 정의 — Major/HIGH (80점)

- **위치**: `deal-mgmt/app/routers/buyer_marketing.py:246-250`
- **교차 검증**: R1 + R5 (2개 에이전트 확인)
- **관점**: R5 의존성 결합도

**문제**: Short-List 정의가 3곳에서 다름:
| 위치 | 정의 |
|------|------|
| `buyer_marketing.py:246` | `tier IS NOT NULL AND tier != NOT_TARGET` |
| `buyers.py:53` | `is_short_listed == True` |
| `ShortListOverview.tsx:358` | `b.is_short_listed` |

`is_short_listed=True` + `tier=NULL` buyer → 마케팅 API에서 누락.

**수정**: `buyer_marketing.py`의 Short-List 필터를 `BuyerCandidate.is_short_listed == True`로 변경.

---

### [P1-3] PATCH `is_short_listed` promotes without validation — Major/HIGH (70점)

- **위치**: `deal-mgmt/app/routers/buyers.py:247-275`
- **관점**: R2 보안

**문제**: `promote-short-list`는 연락처 3필드 필수 검증 후 승격하지만, 일반 PATCH `update_buyer`에서 `is_short_listed: true`를 직접 설정하면 연락처 검증 없이 승격 가능.

```python
# buyers.py:260 — 임의 필드 setattr, is_short_listed 포함
for k, v in update_data.items():
    setattr(buyer, k, v)  # 검증 없이 is_short_listed = True 가능
```

**수정**: `update_buyer`에서 `is_short_listed`를 `exclude_unset` 후 검증하거나, `update_data`에서 `is_short_listed` 제거 후 promote 전용 엔드포인트만 허용.

---

### [P1-4] IDOR — `update_buyer`/`get_buyer`에서 `get_transaction` 미호출 — Major/HIGH (70점)

- **위치**: `deal-mgmt/app/routers/buyers.py:237-245, 292-310`
- **관점**: R2 보안 (Elevation of Privilege)

**문제**: `update_buyer`와 `get_buyer`에서 `txn_id`의 유효성만 `check_client_deal_access`로 확인하고 `get_transaction(db, txn_id)`를 호출하지 않음. 존재하지 않는 `txn_id`로 요청 시 의도하지 않은 동작 가능.

```python
# buyers.py:247 — get_transaction 호출 없음
await check_client_deal_access(db, txn_id, claims)
# 직접 buyer_id로 DB 조회
```

**수정**: `get_transaction(db, txn_id)` 호출 추가 (다른 엔드포인트 `promote_short_list`, `bidding_summary`에서는 이미 호출 중).

---

### [P1-5] Migration 045 `server_default=sa.text("0")` — PostgreSQL Boolean 호환성 위험 — Major/HIGH (80점)

- **위치**: `deal-mgmt/migrations/versions/045_ma_directives_phase1.py:57`
- **교차 검증**: R1 + R3 (2개 에이전트 확인)
- **관점**: R3 데이터 무결성

**문제**: `sa.text("0")`은 SQLite에서 integer 0으로 작동하지만, PostgreSQL Boolean 컬럼에서는 `invalid input syntax for type boolean: "0"` 에러 가능.

```python
# 045:57
server_default=sa.text("0"),  # PostgreSQL에서 위험
```

**수정**: `server_default=sa.false()` (cross-DB 호환 Boolean literal).

---

### [P1-6] FI 추천 쿼리 LIMIT 없는 전체 PEF ORM 로드 — Major/HIGH (80점)

- **위치**: `deal-mgmt/app/routers/pef_registry.py:82-86`
- **교차 검증**: R2 + R5 (2개 에이전트 확인)
- **관점**: R2 DoS + R5 성능

**문제**: 1,137건 PEF 데이터에 LIMIT 없이 전체 ORM 객체 로드 후 Python에서 GP 그룹핑. deal_value 범위에 따라 수백 건 매칭 가능.

```python
pefs = list((await db.execute(q)).scalars().all())  # NO LIMIT
```

**수정**: 필요 컬럼만 SELECT + LIMIT 추가, 또는 DB 레벨 GROUP BY 집계.

---

### [P1-7] `BuyerStatus` 상태 전환 검증 없음 — 임의 역방향 전환 허용 — Major/HIGH (70점)

- **위치**: `deal-mgmt/app/routers/buyers.py:260-263`
- **관점**: R6 도메인 로직

**문제**: PATCH `update_buyer`에 상태 전환 유효성 검증이 전혀 없어 `IDENTIFIED → BID_SUBMITTED`, `REJECTED → LOI_ACCEPTED` 등 현실적으로 불가능한 전환이 허용됨.

**수정**: `_ALLOWED_STATUS_TRANSITIONS` 매트릭스 정의 후 `update_buyer`에서 검증.

---

### [P1-8] `MOU_SIGNED` / `MAIN_DUE_DILIGENCE` 전제조건 부재 — Major/HIGH (70점)

- **위치**: `deal-mgmt/app/services/workflow_engine.py:64-73`
- **관점**: R6 도메인 로직

**문제**: 두 신규 Phase의 전제조건이 빈 리스트(`[]`). 입찰자 0명인 상태에서 MOU 단계 진입 허용.

```python
Phase.MOU_SIGNED: [],           # 전제조건 없음
Phase.MAIN_DUE_DILIGENCE: [],   # 전제조건 없음
```

**수정**: 최소 RECOMMENDED 수준 전제조건 추가 (estimated_deal_value, BID_SUBMITTED buyer 존재 등).

---

### [P1-9] `buyer_summary` 3개 집계 쿼리 순차 실행 — Major/HIGH (70점)

- **위치**: `deal-mgmt/app/routers/buyers.py:71-93`
- **관점**: R5 성능

**문제**: 동일 테이블에 대한 3개 독립 집계 쿼리가 순차 `await` 실행. 단일 쿼리로 통합 가능.

**수정**: CASE WHEN + GROUP BY로 단일 쿼리 통합.

---

### [P1-10] `promote-short-list` 루프 내 audit N코루틴 순차 실행 — Major/HIGH (70점)

- **위치**: `deal-mgmt/app/routers/buyers.py:179-190`
- **관점**: R5 성능

**문제**: N건의 `await audit_service.record()` 순차 호출. 50건 일괄 승격 시 50번의 순차 코루틴 스케줄링.

**수정**: 단일 bulk audit 레코드로 집약 또는 배치 INSERT.

---

## P2 — 개선 권장 (10건)

### [P2-1] `promote-short-list` audit `old_value` 하드코딩 — Moderate/HIGH (50점)

- **위치**: `deal-mgmt/app/routers/buyers.py:185-190`
- **교차 검증**: R3 + R6 (2개 에이전트 확인)
- **관점**: R3 데이터 무결성 + R6 도메인 로직

**문제**: `old_value={"is_short_listed": False}` 하드코딩 → 이미 승격된 buyer 재호출 시 허위 감사 기록.

**수정**: `old_value={"is_short_listed": b.is_short_listed}` 실제 값 참조.

---

### [P2-2] `ShortListOverview` tier-null Short-List buyer UI 누락 — Moderate/HIGH (50점)

- **위치**: `amic-platform/src/modules/ma/components/buyers/ShortListOverview.tsx:369-376`
- **교차 검증**: R5 + R6-UX (2개 에이전트 확인)
- **관점**: R5 결합도 + R6 UX

**문제**: `is_short_listed=true` + `tier=null` buyer가 `TIER_ORDER` 그룹핑에서 누락 → UI에서 보이지 않음.

**수정**: "미분류" 그룹 추가 (`!b.tier || !TIER_ORDER.includes(b.tier)`).

---

### [P2-3] `BUYER_STATUS_VARIANT` BID 3개 상태 누락 — Moderate/HIGH (40점)

- **위치**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:352-370`
- **관점**: R1 정합성

**문제**: `BID_SUBMITTED`, `BID_NOT_SUBMITTED`, `BID_DROPPED` 3개 상태의 variant 매핑 없음 → 기본 variant로 표시.

**수정**: 3개 상태에 대한 variant 추가 (예: `BID_SUBMITTED: "success"`, `BID_NOT_SUBMITTED: "warning"`, `BID_DROPPED: "danger"`).

---

### [P2-4] Migration 046 COMMIT 후 DML 실패 시 롤백 불가 — Moderate/HIGH (50점)

- **위치**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:30-39`
- **교차 검증**: R1 + R5 (2개 에이전트 확인)
- **관점**: R5 배포 안전성

**문제**: `op.execute("COMMIT")` 이후 DML 실패 시 enum 추가는 이미 확정 → 반중간 상태. P0-1 수정 시 위험도 감소.

---

### [P2-5] ILIKE wildcard 미이스케이프 (`%`, `_`) — Moderate/HIGH (50점)

- **위치**: `deal-mgmt/app/routers/pef_registry.py:36`
- **교차 검증**: R2 + R4 (2개 에이전트 확인)
- **관점**: R2 보안 + R4 에러 처리

**문제**: `f"%{search}%"` — 사용자 입력에 `%`, `_` 포함 시 의도하지 않은 와일드카드 매칭.

**수정**: `search.replace("%", r"\%").replace("_", r"\_")` 이스케이프 추가.

---

### [P2-6] `Decimal(str(deal_value))` 변환 예외 미처리 — Moderate/HIGH (40점)

- **위치**: `deal-mgmt/app/routers/pef_registry.py:79`
- **관점**: R4 에러 처리

**문제**: `deal_value`가 NaN/Infinity인 경우 `Decimal` 변환 실패. `deal_value=0`도 빈 결과만 반환 (사용자 피드백 없음).

**수정**: try-except + deal_value ≤ 0 조기 반환.

---

### [P2-7] `FIRecommendModal` API 에러 상태 미처리 — Moderate/HIGH (40점)

- **위치**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx`
- **관점**: R4 에러 처리

**문제**: `isError` 상태 미확인 → API 실패 시 빈 UI 표시. `selected` 상태 모달 재오픈 시 초기화 안 됨.

**수정**: `isError` 조건 분기 + `useEffect` 초기화.

---

### [P2-8] PEF `Decimal` vs FE `number` 정밀도 손실 위험 — Moderate/HIGH (40점)

- **위치**: `deal-mgmt/app/schemas/pef_registry.py:22` ↔ `amic-platform/src/modules/ma/types/pef_registry.ts:9`
- **관점**: R3 API 계약

**문제**: `Numeric(20,2)` → JSON float → JS number. `Number.MAX_SAFE_INTEGER`(~9조) 초과 시 정밀도 손실. PEF 총약정액은 수십조 규모 존재.

---

### [P2-9] 5x 매직 넘버 + `deal_value=0` 미처리 — Moderate/HIGH (40점)

- **위치**: `deal-mgmt/app/routers/pef_registry.py:80`
- **관점**: R6 도메인 로직

**문제**: `upper_bound = deal_value_dec * 5` — 비즈니스 근거 미명시. `deal_value=0` → 빈 결과 조용히 반환.

**수정**: 상수 추출 + 주석 + 경계값 처리.

---

### [P2-10] `pef_registry` 라우터의 `transaction_service` 직접 의존 — Moderate/HIGH (40점)

- **위치**: `deal-mgmt/app/routers/pef_registry.py:18,72`
- **관점**: R5 의존성 결합도

**문제**: PEF 도메인 라우터가 Transaction 모델에 직접 의존. `getattr(txn, "estimated_deal_value", None)` 방어적 접근 자체가 불안정성 인지 증거.

---

## P3 — 저우선 (8건)

### [P3-1] `buyers.py` logger 선언 후 미사용 — Minor/HIGH (20점)

- **위치**: `deal-mgmt/app/routers/buyers.py:29`
- **관점**: R4 관찰 가능성

**문제**: `logger = logging.getLogger(__name__)` 선언 후 전체 파일에서 한 번도 사용하지 않음. promote/bidding-summary 등 중요 비즈니스 동작에 로깅 없음.

---

### [P3-2] `seed_pef_registry.py` print-only 로깅 + openpyxl 에러 미처리 — Minor/HIGH (20점)

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py`
- **관점**: R4 관찰 가능성

**문제**: `print()` 사용 (구조화 로깅 없음). xlsx 파일 열기/파싱 에러 미처리.

---

### [P3-3] `COL_MAP` 정의 후 미사용 — 인덱스 직접 하드코딩 — Minor/HIGH (20점)

- **위치**: `deal-mgmt/scripts/seed_pef_registry.py:32-40,70-78`
- **관점**: R6 가독성

---

### [P3-4] `test_new_buyer_status_values` — 잘못된 비즈니스 규칙 검증 — Minor/HIGH (20점)

- **위치**: `deal-mgmt/tests/test_short_list_promotion.py:104-115`
- **관점**: R6 테스트 품질

**문제**: `IDENTIFIED → BID_SUBMITTED` 직접 전환을 200으로 단언 → 상태 전환 제약 추가 시 깨짐.

---

### [P3-5] `buyer_ids` 크기 제한 없음 — Minor/MEDIUM (12점)

- **위치**: `deal-mgmt/app/schemas/buyer.py:86`
- **관점**: R2 DoS

**문제**: `buyer_ids: list[uuid.UUID]` — 수천 건 전송 시 성능 저하.

---

### [P3-6] `is_short_listed=false` 필터 테스트 부재 — Minor/MEDIUM (12점)

- **위치**: `deal-mgmt/tests/test_short_list_promotion.py:81-98`
- **관점**: R6 테스트 품질

---

### [P3-7] `FIRecommendModal` checkbox `aria-label` 누락 — Minor/HIGH (20점)

- **위치**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx`
- **관점**: R6 접근성

---

### [P3-8] `ShortListOverview` `window.confirm` 비접근성 — Minor/HIGH (20점)

- **위치**: `amic-platform/src/modules/ma/components/buyers/ShortListOverview.tsx`
- **관점**: R6 UX 접근성

---

## BE Pydantic ↔ FE TypeScript 필드 대조표

### `BuyerCandidateUpdate` (P0-3 원인)

| 필드 | BE (buyer.py) | FE (buyer.ts) | 일치 |
|------|-------------|-------------|------|
| company_name ~ extra_data (16개) | ✅ | ✅ | ✅ |
| **is_short_listed** | `bool \| None = None` | **없음** | **❌ Critical** |

### `BuyerCandidate` Response

| 필드 | BE | FE | 일치 |
|------|----|----|------|
| 20개 필드 모두 | ✅ | ✅ | ✅ |
| is_short_listed | `bool = False` | `boolean` | ✅ |

### `PefFund` / `FIRecommendation`

| 필드 | BE | FE | 일치 |
|------|----|----|------|
| 기본 필드 | ✅ | ✅ | ✅ |
| total_committed_capital | `Decimal` | `number` | ⚠️ 정밀도 |
| total_committed_sum | `Decimal` | `number` | ⚠️ 정밀도 |

---

## Short-List 정의 불일치 매트릭스 (P1-2 원인)

| 위치 | 정의 | 문제 |
|------|------|------|
| `buyer_marketing.py:246` | `tier IS NOT NULL AND tier != NOT_TARGET` | **❌ tier 기반** |
| `buyers.py:53` | `is_short_listed == True` | ✅ 플래그 기반 |
| `ShortListOverview.tsx:358` | `b.is_short_listed` | ✅ 플래그 기반 |
| `ShortListOverview.tsx:369` | `TIER_ORDER.filter(tier === b.tier)` | **⚠️ tier 그룹핑** |

---

## 쿼리 키 불일치 매트릭스 (P1-1 원인)

| Hook | 현재 키 | 표준 패턴 | 일치 |
|------|--------|---------|------|
| `useTransactions` | `["ma", "transactions", ...]` | — | ✅ 기준 |
| `useBuyers` | `["ma", "transactions", txnId, "buyers"]` | — | ✅ |
| `useFIRecommendations` | `["fi-recommendations", txnId]` | `["ma", "transactions", txnId, "fi-recommendations"]` | ❌ |
| `useBiddingSummary` | `["bidding-summary", txnId]` | `["ma", "transactions", txnId, "bidding-summary"]` | ❌ |
| `usePromoteShortList.onSuccess` | `["buyers", txnId]` | `["ma", "transactions", txnId, "buyers"]` | ❌ 무효화 미동작 |

---

## R2 보안 + 위협 모델링 상세

### STRIDE 위협 분석

| 위협 | 대상 | 이슈 | 상태 |
|------|------|------|------|
| **Spoofing** | — | JWT 인증 정상 적용 | ✅ |
| **Tampering** | PATCH is_short_listed | promote 검증 우회 가능 | P1-3 |
| **Repudiation** | audit old_value | 하드코딩으로 허위 기록 | P2-1 |
| **Info Disclosure** | 422 응답 | 내부 필드명 노출 (contact_name 등) | Note |
| **DoS** | FI 추천 | LIMIT 없는 전체 로드 | P1-6 |
| **Elevation** | update_buyer IDOR | get_transaction 미호출 | P1-4 |

---

## R5 성능 분석 상세

| 위치 | 유형 | 영향 | 이슈 |
|------|------|------|------|
| `buyers.py:71-93` | 3쿼리 순차 | 200ms 목표 초과 가능 | P1-9 |
| `buyers.py:179-190` | N코루틴 순차 | 50건 시 누적 지연 | P1-10 |
| `pef_registry.py:82-86` | LIMIT 없는 ORM | 메모리 선형 증가 | P1-6 |

---

## R6 도메인 로직 상세

### 상태 전환 규칙 부재 (P1-7)

현재: 17개 BuyerCandidateStatus 간 임의 전환 허용
필요: 단방향 파이프라인 (IDENTIFIED → CONTACTED → NDA_SENT → ... → BID_SUBMITTED)

### Phase 전제조건 비교

| Phase | 전제조건 | 평가 |
|-------|---------|------|
| ENGAGEMENT | — | ✅ |
| PREPARATION | engagement_document | ✅ |
| MARKETING | estimated_deal_value | ✅ |
| BIDDING | deal_structure | ✅ |
| **MOU_SIGNED** | **없음** | **❌ P1-8** |
| **MAIN_DUE_DILIGENCE** | **없음** | **❌ P1-8** |
| NEGOTIATION | — | ✅ |
| CLOSING | risk + compliance gate | ✅ |
| POST_CLOSING | — | ✅ |

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 46건
- 거부된 가설 (사전 제거): 10건
- 보고된 이슈: 31건 (48건 발견 → 17건 중복 병합)
- 거부율: 22%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | `UUID(as_uuid=True)` pre-existing → 1,031 테스트 통과 |
| Self-Challenge 기각 | 3 | SC-5: `ioi_value: number`가 프로젝트 전체 일관 패턴 |
| 이미 구현됨 | 2 | PEF 라우터 main.py 등록 → line 203에 존재 |
| 범위 외 | 1 | AUTH_ENABLED=False → 프로덕션 ENV guard 존재 |
| 중복 | 1 | list_buyers 전체 로드 가설 → DB WHERE 필터 확인 |

### 교차 검증 매트릭스

| 이슈 | R1 | R2 | R3 | R4 | R5 | R6 | UX |
|------|----|----|----|----|----|----|-----|
| P0-1 Migration 046 | ✅ | | ✅ | | ✅ | | |
| P0-2 SQL Injection | ✅ | ✅ | | | | ✅ | |
| P0-3 FE is_short_listed | ✅ | | ✅ | | | | |
| P1-1 쿼리 키 | ✅ | | ✅ | | ✅ | | |
| P1-2 tier 기반 | ✅ | | | | ✅ | | |
| P1-5 server_default | ✅ | | ✅ | | | | |
| P1-6 LIMIT 없음 | | ✅ | | | ✅ | | |
| P2-1 audit old_value | | | ✅ | | | ✅ | |
| P2-2 tier-null 누락 | | | | | ✅ | | ✅ |
| P2-4 COMMIT 롤백 | ✅ | | | | ✅ | | |
| P2-5 ILIKE escape | | ✅ | | ✅ | | | |

---

## Methodology

- **Agents**: backend-security-reviewer(R2), migration-validator(R3), performance-profiler(R5), python-code-reviewer(R6), Explore(R4), Direct analysis(R6-UX)
- **Files scanned**: 15+ 파일 (routers, schemas, models, migrations, hooks, types, components)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major (교차 검증 11건)
- **Total agent findings**: 48건 → 중복 병합 17건 → 최종 31건
