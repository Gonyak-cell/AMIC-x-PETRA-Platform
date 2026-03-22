# Code Review — Short-List Tier 기반 자동 승격

> **Review Date**: 2026-03-09 13:39
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 커밋 `6ccfeed` — deal-mgmt BE 3파일 + amic-platform FE 8파일 = 11파일
> **Method**: Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: ruff(PASS) pytest(PASS) tsc(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(code-reviewer ×2)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 1     | HIGH: 1 | P1: 1 |
| Moderate | 2     | MEDIUM: 2 | P3: 2 |
| Minor    | 1     | HIGH: 1 | P3: 1 |
| **Total**| **4** | HIGH: **2** / MEDIUM: **2** | P1: **1** / P3: **3** |

**FP Prevention**: 가설 8건 검증, 2건 사전 거부 (거부율: 25%) | 교차 검증 3건 수행 (1건 PARTIAL 하향)

---

## Findings

### [BE-1] add_buyer audit 로그에 Tier 동기화 값 누락 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/app/routers/buyers.py:160`

**증거**:
```python
# 라인 147-160
data = body.model_dump()
# Tier → is_short_listed 자동 동기화
if data.get("tier") in (BuyerTier.TIER_1, BuyerTier.TIER_2, BuyerTier.TIER_3):
    data["is_short_listed"] = True
buyer = BuyerCandidate(transaction_id=txn_id, **data)
...
await audit_service.record(
    ...
    new_value=body.model_dump(mode="json"),  # ← 동기화 전 원본 사용
)
```

**문제**: `audit_service.record`가 `body.model_dump()` (동기화 전 원본)을 사용하므로, `tier=TIER_1`로 생성 시 실제로는 `is_short_listed=True`가 설정되지만 감사 로그에는 미반영.

**비교**: `update_buyer`(라인 260-271)에서는 `update_data`를 사용하므로 동기화 값이 정확히 기록됨.

**교차 검증**: CONFIRMED — Read로 라인 160 직접 확인.

**권장 수정**: `body.model_dump(mode="json")` → 동기화 반영된 `data`로 교체.

---

### [BE-2] is_short_listed 직접 PATCH 시 Tier와 비정합 가능 — [Moderate/MEDIUM ⚠️] — Priority: P3 (점수: 24)

**파일**: `deal-mgmt/app/routers/buyers.py:252-258`

**증거**:
```python
# 라인 252: Tier가 update_data에 있을 때만 동기화 발동
if "tier" in update_data:
    ...
```

`is_short_listed`만 단독 PATCH하면 Tier 상태와 무관하게 변경 가능 → `tier=TIER_1` + `is_short_listed=False` 비정합 상태 발생 가능.

**교차 검증**: DESIGN_RISK — `test_toggle_short_listed_via_patch` 테스트가 의도적으로 존재. 직접 override를 허용하는 설계 결정으로 판단.

**권장**: 의도된 동작이라면 코드 주석으로 명시. 의도가 아니라면 `is_short_listed` 직접 설정을 차단하고 Tier로만 제어.

---

### [BE-3] add_buyer Tier 동기화 로직이 update_buyer와 비대칭 — [Moderate/MEDIUM ⚠️] — Priority: P3 (점수: 24)

**파일**: `deal-mgmt/app/routers/buyers.py:148-150`

**증거**:
```python
# add_buyer: TIER_1/2/3일 때만 True 설정 (False는 모델 기본값에 의존)
if data.get("tier") in (BuyerTier.TIER_1, BuyerTier.TIER_2, BuyerTier.TIER_3):
    data["is_short_listed"] = True

# update_buyer: tier 키 존재 시 True/False 명시적 할당
if "tier" in update_data:
    update_data["is_short_listed"] = new_tier in (TIER_1, TIER_2, TIER_3)
```

결과적으로 동일하게 동작하지만 패턴이 비대칭. `add_buyer`에서도 `update_buyer`와 동일 패턴으로 통일 권장:
```python
if data.get("tier") is not None:
    data["is_short_listed"] = data["tier"] in (BuyerTier.TIER_1, BuyerTier.TIER_2, BuyerTier.TIER_3)
```

---

### [FE-1] devMockBuyers 함수 호출에 useMemo 누락 — [Minor/HIGH ⚠️] — Priority: P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx:221-222`

**증거**:
```tsx
const DEV_MOCK_BUYERS = createDevMockBuyers(txnId);
const DEV_MOCK_OVERVIEW = createDevMockOverview();
```

매 렌더링마다 새 배열 참조 생성. 하위 컴포넌트 불필요한 재렌더링 유발.

**교차 검증**: PARTIAL — 프로덕션에서 `import.meta.env.DEV` 가드로 빈 배열(`[]`) 반환하므로 실제 영향은 Dev 환경으로 한정. FE 에이전트의 Major → Minor로 하향 조정.

**권장**: `useMemo`로 감싸면 Dev 환경에서도 참조 안정성 확보.
```tsx
const DEV_MOCK_BUYERS = useMemo(() => createDevMockBuyers(txnId), [txnId]);
const DEV_MOCK_OVERVIEW = useMemo(() => createDevMockOverview(), []);
```

---

## 거부된 이슈 (Phase 2에서 제거/하향)

| 원본 | 거부 사유 | 분류 |
|------|----------|------|
| FE I-2 (BuyerDetailPanel scrollTo 타이밍) | 옵셔널 체이닝으로 크래시 방지. 간헐적 실패 가능성만 있으며 현재 재현 불가 | FP-SEV |
| BE Issue-4 (스키마 is_short_listed 잔존) | BE-2와 동일 설계 결정. 별도 이슈로 분리 불필요 | 중복 |

---

## 잘 된 점

1. **SSOT 달성**: Tier가 is_short_listed의 유일한 파생 원천으로 전환 완료
2. **Dead code 완전 정리**: `ShortListPromoteRequest`, `usePromoteShortList`, 체크박스 컬럼, 연락처 검증 — 잔존 참조 0건 (Grep 확인)
3. **테스트 커버리지**: Tier 동기화의 8개 경로 전부 테스트 (생성/수정/승격/해제/null/연락처불필요)
4. **감사 로그 유지**: `update_buyer`에서 Tier→is_short_listed 변경이 정확히 기록됨
5. **보안**: `promote-short-list` 엔드포인트 삭제 후 라우트 충돌 없음. 인증 Depends 유지 확인
6. **FE 접근성**: SIMappingPanel `aria-live`, KanbanView `aria-label`, Button `aria-busy` 자동 설정 확인

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. [BE-1] [Major/HIGH]: add_buyer audit 로그에 Tier 동기화 값 누락 — buyers.py:160 (점수: 70)

### P3 — 저우선 (점수: <30)
1. [BE-2] [Moderate/MEDIUM ⚠️]: is_short_listed 직접 PATCH 비정합 — buyers.py:252 (점수: 24, 설계 결정)
2. [BE-3] [Moderate/MEDIUM ⚠️]: add_buyer/update_buyer 동기화 로직 비대칭 — buyers.py:148 (점수: 24)
3. [FE-1] [Minor/HIGH ⚠️]: devMockBuyers useMemo 누락 — BuyersTab.tsx:221 (점수: 20, Dev 전용)

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | 연락처 검증 제거 + Tier 동기화 추가 | ✅ | buyers.py:148-150, 252-258 |
| 2 | ShortListPromoteRequest 삭제 | ✅ | buyer.py diff, Grep 참조 0건 |
| 3 | 테스트 전면 개정 | ✅ | 13 tests passed |
| 4 | 체크박스 컬럼 제거 | ✅ | BuyersTab.tsx diff |
| 5 | usePromoteShortList 삭제 | ✅ | usePefRegistry.ts diff |
| 6 | FE ShortListPromoteRequest 삭제 | ✅ | buyer.ts diff |

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| ruff check + format | ✅ PASS | §1 정합성 자동 검증됨 |
| pytest (13/13) | ✅ PASS | §2 완전성 자동 검증됨 |
| tsc --noEmit | ✅ PASS | §1 타입 정합성 자동 검증됨 |

---

## Methodology

- Agents: code-reviewer (BE), code-reviewer (FE)
- Excluded Agents: type-checker, api-auditor, security-auditor, a11y-auditor (quick review)
- Files scanned: 11
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: Major 3건 수행 (CONFIRMED 1, DESIGN_RISK 1, PARTIAL 1)
- Backend availability: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 8건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 4건
- 거부율: 25%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 심각도 과대 (FP-SEV) | 1 | scrollTo 타이밍 — 크래시 방지 코드 존재 |
| 중복 | 1 | 스키마 is_short_listed 잔존 — BE-2와 동일 설계 결정 |
