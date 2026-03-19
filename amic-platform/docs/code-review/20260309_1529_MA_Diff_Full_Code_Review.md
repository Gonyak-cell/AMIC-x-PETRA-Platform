# Code Review — MA Diff (feat/ma-workflow)

> **Review Date**: 2026-03-09 15:29
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff HEAD` — 18개 변경 파일 (Short List 녹색 통일 + R03-R06 수정)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification + Auto-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(PASS 178/178) build(PASS)
> **Review Gates**: Backend(unavailable) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2                | P0: 2               |
| Major    | 4     | HIGH: 4                | P1: 4               |
| Moderate | 3     | HIGH: 2 / MEDIUM: 1    | P2: 3               |
| Minor    | 1     | MEDIUM: 1              | P3: 1               |
| **Total**| **10**| HIGH: **8** / MEDIUM: **2** | P0: **2** / P1: **4** / P2: **3** / P3: **1** |

**FP Prevention**: 가설 14건 검증, 4건 사전 거부 (거부율: 29%) | 교차 검증 2건 수행 (Critical)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 2건 하향 조정 (Moderate→P2, Minor→P3)

---

## Findings

### [API-06] DealSetup onError 이중 토스트 — [Critical/HIGH] — Priority: P0 (100)

**파일**: `src/modules/ma/hooks/useDealSetup.ts` (18-20, 37-39, 57-59행)
+ `src/modules/ma/pages/DealSetupWizardPage.tsx` (395, 406, 424행)

**문제**: `useDealSetup.ts`의 3개 mutation 훅(`useDealSetupFromText`, `useDealSetupFromExcel`, `useConfirmDealSetup`) 모두 `onError`에서 `toast.error()`를 호출한다. 그런데 `DealSetupWizardPage.tsx`에서 `.mutate()` 호출 시 **또 다른 `onError`**를 전달하여 이중 토스트가 발생한다.

**증거**:
```typescript
// useDealSetup.ts:18-20
onError: () => toast.error("텍스트 파싱에 실패했습니다."),

// DealSetupWizardPage.tsx:395
textMut.mutate(text, { onError: () => toast.error("...") });
```

React Query는 hook-level과 `.mutate()` call-level의 `onError`를 **모두** 실행하므로, 에러 발생 시 사용자에게 토스트가 2번 표시된다.

**권장 수정**: hook-level `onError` 제거하고, 호출 측에서만 `onError` 처리. 또는 `.mutate()` 호출 시 `onError` 제거.

**검증**: Phase 2 교차 검증 CONFIRMED — `useDealSetup.ts` 직접 Read하여 3개 훅 모두 동일 패턴 확인.

---

### [A11Y-007] useFocusTrap 포커스 복원 누락 — [Critical/HIGH] — Priority: P0 (100)

**파일**: `src/modules/ma/hooks/useFocusTrap.ts` (전체)

**문제**: ARIA Dialog Pattern의 MUST 요구사항인 "다이얼로그 닫힐 때 이전 포커스 위치로 복원"이 구현되어 있지 않다. 현재 `useEffect` cleanup에서 `removeEventListener`만 수행하고, 다이얼로그 열기 전 `document.activeElement`를 저장/복원하는 로직이 없다.

**증거**:
```typescript
// useFocusTrap.ts — useEffect cleanup
return () => document.removeEventListener("keydown", handleKeyDown);
// ❌ previouslyFocused 저장/복원 없음
```

**영향**: 스크린 리더 사용자가 다이얼로그를 닫은 후 포커스가 `<body>`로 이동하여 페이지 처음부터 다시 탐색해야 함.

**권장 수정**:
```typescript
useEffect(() => {
  if (!open) return;
  const previouslyFocused = document.activeElement as HTMLElement | null;
  // ... existing logic
  return () => {
    document.removeEventListener("keydown", handleKeyDown);
    previouslyFocused?.focus();
  };
}, [open, handleKeyDown, dialogRef]);
```

**검증**: Phase 2 교차 검증 CONFIRMED — `useFocusTrap.ts` 직접 Read하여 cleanup 로직 확인.

---

### [ISS-3/API-02/API-03/SEC-02] VdrTab 재시도 로직 — [Major/HIGH] — Priority: P1 (80, 교차 검증 +10)

**파일**: `src/modules/ma/components/vdr/VdrTab.tsx` (catch 블록)

**문제**:
1. **백오프 없음**: 재시도 간격 없이 즉시 `qc.invalidateQueries()`로 재시도. 서버 과부하 시 연쇄 실패 가능.
2. **ref 리셋**: `autoInitRef`와 `retryCountRef`가 컴포넌트 리마운트 시 리셋되어 무한 재시도 가능.
3. **패턴 혼용**: 직접 `maApi.post()` 호출 vs `useMutation` — 같은 컴포넌트 내 API 호출 패턴 불일치.

**검증**: code-reviewer + api-auditor + security-auditor 3개 에이전트 교차 발견.

---

### [API-01] FI 배치 동시성 무제한 — [Major/HIGH] — Priority: P1 (70)

**파일**: `src/modules/ma/components/buyers/FIRecommendModal.tsx` (77-84행)

**문제**: `Promise.allSettled(toAdd.map(b => maApi.post(...)))` — 모든 POST 요청을 동시에 발사. 배치 크기 제한(chunk/throttle) 없음. 다만 실제 FI 추천은 50건 이내여서 실질적 위험도는 중간.

**권장 수정**: `p-limit` 라이브러리 또는 수동 chunk 분할 (5건씩 등).

---

### [API-05] useVdr.ts extractApiError 미사용 — [Major/HIGH] — Priority: P1 (70)

**파일**: `src/modules/ma/hooks/useVdr.ts` (76, 102, 119, 171, 203, 225, 251행)

**문제**: 7개 mutation의 `onError`에서 `extractApiError`를 사용하지 않고 하드코딩된 한국어 메시지만 사용. 서버가 구체적 에러 메시지(예: "문서가 존재하지 않습니다")를 반환해도 항상 "문서 생성에 실패했습니다" 같은 일반 메시지만 표시.

**Phase 2B 검증**: verified (score: 90) — Grep으로 extractApiError import 0건 확인.

---

### [SEC-01] extractApiError 5xx 메시지 필터링 없음 — [Major/HIGH] — Priority: P1 (70)

**파일**: `src/api/errors.ts` (14-15행)

**문제**: `extractApiError`가 서버 응답의 `detail` 문자열을 무조건 반환. 5xx 에러 시 서버 내부 메시지(DB 에러, 스택 트레이스 등)가 `detail`에 포함되면 사용자에게 그대로 노출 가능.

**권장 수정**: HTTP status >= 500일 때 fallback 메시지를 반환하도록 분기 추가.

**Phase 2B 검증**: verified (score: 80) — FastAPI 기본 500은 보통 detail 미포함이므로 실질적 위험도는 보고보다 다소 낮음.

---

### [ISS-5/API-07] DealSetup extractApiError 미사용 — [Moderate/HIGH] — Priority: P2 (40)

**파일**: `src/modules/ma/hooks/useDealSetup.ts`

**문제**: API-05와 동일 패턴. 3개 mutation 모두 하드코딩 에러 메시지 사용. 서버 에러 세부사항이 사용자에게 전달되지 않음.

**Phase 2B 검증**: verified (score: 90).

---

### [TC-01] TIER_STYLES 느슨한 타입 — [Moderate/HIGH] — Priority: P2 (40)

**파일**: `src/modules/ma/components/buyers/BuyerTierBadge.tsx` (6행)

**문제**: `Record<string, string>` 대신 `Record<BuyerTier, string>`을 사용하면 키 누락/오타를 컴파일 타임에 잡을 수 있음. `BuyerTier` 타입은 이미 import(3행)하고 있으나 활용하지 않음.

**Phase 2B 검증**: verified (score: 85).

---

### [A11Y-001/002/003] 색상 대비 부족 — [Moderate/MEDIUM] — Priority: P2 (24)

**파일**: `BuyerTierBadge.tsx`, `DealRoleBadge.tsx`, `ShortListSummaryBar.tsx`

**문제**: `text-accent` (#26C260) on `bg-accent-light` (#E8F8ED) ≈ 2.5:1 비율. WCAG AA 소형 텍스트 최소 4.5:1 미달. `ShortListSummaryBar`의 `text-accent` on `bg-white` ≈ 3.5:1도 미달이나, `text-lg font-bold` 대형 텍스트에는 3:1 충족 가능.

**권장 수정**: `text-accent` 대신 `text-amic-400` (#3D7D6E, 더 짙은 녹색) 사용하면 대비 개선.

**Phase 2B 검증**: verified (score: 80) — tailwind.config.js에서 색상값 직접 확인.

---

### [API-04] useUpdateVdrDocument 과도한 캐시 무효화 — [Minor/MEDIUM] — Priority: P3 (12)

**파일**: `src/modules/ma/hooks/useVdr.ts` (193-200행)

**문제**: 문서 1건 수정 시 VDR 하위 전체 쿼리 + 부모 트랜잭션 쿼리까지 무효화. 불필요한 리페치 유발.

**Phase 2B 검증**: verified (score: 85).

---

## 거부된 이슈 (False Positives)

### [ISS-1/API-08] failedNames 인덱스 매핑 — REJECTED (Phase 2B)

**사유**: FP-HALLUC — 보고된 `results.indexOf(r)` 패턴이 실제 코드에 존재하지 않음. 실제 코드(96행)는 `results.flatMap((r, i) => r.status === 'rejected' ? [toAdd[i]] : [])` 로 인덱스 기반 정확한 매핑 사용 중.

### [SEC-03/TC-03] err.message 직접 사용 — REJECTED (Phase 2B)

**사유**: FP-LINE — useVdr.ts에 `err.message` 패턴 0건. 해당 패턴은 `useTransactions.ts`, `useMarketingLogs.ts`, `useAttachments.ts`에 존재하나 보고된 파일과 불일치.

### [ISS-2/TC-02] Badge variant+className 충돌 — REJECTED (Phase 1)

**사유**: FP-IMPL — `cn()` 유틸리티가 `twMerge(clsx(inputs))`를 사용하므로 variant와 className의 Tailwind 클래스 충돌은 자동 해결됨.

### [A11Y-005] Backdrop 클릭 닫기 없음 — REJECTED (Phase 1)

**사유**: FP-CTX — 린터가 `onClick={onClose}`를 backdrop에, `onClick={(e) => e.stopPropagation()}`를 inner div에 자동 추가하여 이미 수정됨.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 기능 정확성/접근성)
1. [API-06] [Critical/HIGH]: DealSetup onError 이중 토스트 — `useDealSetup.ts` + `DealSetupWizardPage.tsx` (점수: 100)
2. [A11Y-007] [Critical/HIGH]: useFocusTrap 포커스 복원 누락 — `useFocusTrap.ts` (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/보안)
1. [ISS-3/API-02/API-03/SEC-02] [Major/HIGH]: VdrTab 재시도 로직 (백오프 없음, 패턴 혼용) — `VdrTab.tsx` (점수: 80, 교차 검증)
2. [API-01] [Major/HIGH]: FI 배치 동시성 무제한 — `FIRecommendModal.tsx` (점수: 70)
3. [API-05] [Major/HIGH]: useVdr.ts extractApiError 미사용 — `useVdr.ts` (점수: 70)
4. [SEC-01] [Major/HIGH]: extractApiError 5xx 메시지 필터링 없음 — `errors.ts` (점수: 70)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [ISS-5/API-07] [Moderate/HIGH]: DealSetup extractApiError 미사용 — `useDealSetup.ts` (점수: 40)
2. [TC-01] [Moderate/HIGH]: TIER_STYLES 느슨한 타입 — `BuyerTierBadge.tsx` (점수: 40)
3. [A11Y-001/002/003] [Moderate/MEDIUM]: 색상 대비 부족 — 3개 파일 (점수: 24)

### P3 — 저우선 (점수: <30, 개선 가능)
1. [API-04] [Minor/MEDIUM]: useUpdateVdrDocument 과도한 캐시 무효화 — `useVdr.ts` (점수: 12)

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | ShortListSummaryBar 카드 색상 → 녹색 계열 | ✅ | `ShortListSummaryBar.tsx`:41-46 |
| 2 | DealRoleBadge 역할 배지 → 녹색 계열 | ✅ | `DealRoleBadge.tsx`:5-10 |
| 3 | BuyerTierBadge Tier 배지 → 녹색 계열 | ✅ | `BuyerTierBadge.tsx`:6-11 |
| 4 | R03: FIRecommendModal 에러 핸들링 | ✅ | `FIRecommendModal.tsx`:77-100 |
| 5 | R04: VdrTab 캐시 무효화 | ✅ | `VdrTab.tsx`:catch 블록 |
| 6 | R05: 포커스 트랩 공유 훅 | ✅ | `useFocusTrap.ts` (신규) |
| 7 | R06: BuyerFeedbackSection extractApiError | ✅ | `BuyerFeedbackSection.tsx`:27 |

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | §1 정합성 자동 검증됨 |
| ESLint | ✅ PASS | §1 정합성 자동 검증됨 |
| Vitest (178/178) | ✅ PASS | §2 완전성 자동 검증됨 |
| Vite build | ✅ PASS | §1 정합성 자동 검증됨 |

---

## Methodology

- **Agents**: code-reviewer, type-checker, security-auditor, a11y-auditor, api-auditor (5개)
- **Excluded Agents**: 없음
- **Files scanned**: 18개 (diff 범위)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 2건 수행 (2건 CONFIRMED)
- **Auto-verification**: Moderate/Minor 9건 수행 (7건 verified, 2건 rejected)
- **Backend availability**: FDD(unavailable) KIIS(unavailable) IM(unavailable)

## 검증 투명성

### 검증 통계
- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 4건
- 보고된 이슈: 10건
- 거부율: 29%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| FP-HALLUC (코드 스니펫 허위) | 1 | ISS-1: `results.indexOf(r)` 실제 미존재 |
| FP-LINE (파일 위치 오보) | 1 | SEC-03: useVdr.ts에 err.message 미존재 |
| FP-IMPL (구현 이해 부족) | 1 | ISS-2: cn() → twMerge 자동 해결 |
| FP-CTX (컨텍스트 미반영) | 1 | A11Y-005: 린터가 이미 자동 수정 |

### Phase 2B 자동 검증 상세

| 이슈 | 점수 | 판정 |
|------|------|------|
| ISS-5/API-07 | 90 | verified |
| API-05 | 90 | verified |
| TC-01 | 85 | verified |
| API-01 | 85 | verified |
| API-04 | 85 | verified |
| A11Y-001/002/003 | 80 | verified |
| SEC-01 | 80 | verified |
| ISS-1/API-08 | 25 | **flagged → rejected** |
| SEC-03/TC-03 | 30 | **flagged → rejected** |
