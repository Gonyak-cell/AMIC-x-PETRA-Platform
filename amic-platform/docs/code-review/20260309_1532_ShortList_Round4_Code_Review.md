# Code Review — Short List 탭 4차 리뷰

> **Review Date**: 2026-03-09 15:32
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Short List 탭 구현 변경 파일 — 13개 리뷰 관점 심층 리뷰
> **Method**: Review Gates (skip) + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: --skip-gates
> **Round**: 4차 (이전 3차 리뷰에서 단순 이슈 수정 완료 후 잔여 이슈 탐색)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 8     | HIGH: 6 / MEDIUM: 2 / LOW: 0 | P1: 4 / P2: 4 |
| Moderate | 0     | — | — |
| Minor    | 0     | — | — |
| **Total**| **8** | HIGH: **6** / MEDIUM: **2** / LOW: **0** | P1: **4** / P2: **4** |

**FP Prevention**: 가설 10건 검증, 2건 사전 거부 (거부율: 20%) | 교차 검증 8건 수행
**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 2건 하향 조정 (Major/MEDIUM → P2)

## Findings

---

### [R4-2 + SEC-R4-01] FIRecommendModal 부분 실패 시 중복 제출 + 훅 우회 — [Major/HIGH] — Priority: P1

**점수**: 80 (교차 검증 +10 보너스)

**위치**: `src/modules/ma/components/buyers/FIRecommendModal.tsx:88-111`

**문제**:
1. `Promise.allSettled` 부분 실패 시 성공한 GP가 `selected` 상태에서 제거되지 않아 재시도 시 중복 POST 발생
2. `maApi.post()` 직접 호출 — `useAddBuyer` 훅을 우회하여 캐시 무효화 누락
3. `setIsSubmitting(true)` → `await` → `setIsSubmitting(false)` 패턴에서 더블클릭 방지 불완전

**현재 코드**:
```tsx
const results = await Promise.allSettled(
  toAdd.map((buyer) =>
    maApi.post(`/transactions/${txnId}/buyers`, { /* ... */ })
  )
);
const rejected = results.filter((r) => r.status === "rejected");
if (rejected.length > 0) {
  const failedNames = results.flatMap((r, i) =>
    r.status === "rejected" ? [toAdd[i]] : [],
  );
  toast.error(`${failedNames.join(", ")} 추가 실패`);
}
// ⚠️ 성공한 항목을 selected에서 제거하지 않음
// ⚠️ useAddBuyer 훅 대신 maApi.post 직접 호출
```

**수정 방안**:
1. 부분 성공 시 성공 항목을 `selected`에서 제거
2. `useAddBuyer` 훅 사용 또는 성공 후 queryClient.invalidateQueries 호출
3. `<button disabled={isSubmitting}>` 추가

**확정 근거**: Read로 FIRecommendModal.tsx:88-111 직접 확인, Promise.allSettled 후 selected 상태 미정리 확인

---

### [A11Y-R4-01] DartCompanyTypeahead ARIA combobox 패턴 불완전 — [Major/HIGH] — Priority: P1

**점수**: 70

**위치**: `src/modules/ma/components/buyers/DartCompanyTypeahead.tsx:116-158`

**문제**: WAI-ARIA combobox 패턴 필수 속성 누락
- `role="combobox"` 있으나 `aria-controls` 없음 (listbox id 연결 필요)
- `aria-activedescendant` 없음 (키보드 탐색 시 현재 선택 항목 전달)
- `role="listbox"` (line 145)에 `id` 없음
- `role="option"` (line 158)에 개별 `id` 없음

**수정 방안**:
- listbox에 `id="dart-company-listbox"` 추가
- input에 `aria-controls="dart-company-listbox"` 추가
- 각 option에 `id={`dart-option-${index}`}` 추가
- 키보드 하이라이트 시 `aria-activedescendant` 업데이트 (현재 키보드 탐색 미구현이면 향후 과제)

**확정 근거**: Read로 DartCompanyTypeahead.tsx:116-158 직접 확인

---

### [A11Y-R4-02] LongListFilters 접근성 레이블 누락 — [Major/HIGH] — Priority: P1

**점수**: 70

**위치**: `src/modules/ma/components/buyers/LongListFilters.tsx:39-59`

**문제**: 3개 `<Select>` 컴포넌트에 접근성 레이블 없음
- 산업 필터 (line 39)
- 매각 적합성 필터 (line 47)
- 전략적합성 필터 (line 55)

스크린 리더에서 "콤보박스" 등 역할만 읽히고 용도를 알 수 없음.

**수정 방안**: 각 Select에 `aria-label` 속성 추가
```tsx
<Select aria-label="산업 필터" ...>
<Select aria-label="매각 적합성 필터" ...>
<Select aria-label="전략적합성 필터" ...>
```

**확정 근거**: Read로 LongListFilters.tsx:39-59 직접 확인

---

### [A11Y-R4-03] InlineLogInput 폼 요소 레이블 누락 — [Major/HIGH] — Priority: P1

**점수**: 70

**위치**: `src/modules/ma/components/buyers/InlineLogInput.tsx:86-113`

**문제**: 3개 폼 요소에 `<label>` 또는 `aria-label` 없음
- `<select>` (접촉 유형 선택, line ~86)
- `<input type="date">` (날짜 선택, line ~95)
- `<input type="text">` (내용 입력, line ~105)

이 컴포넌트는 ShortListOverview, BuyerDetailPanel 등 4+ 위치에서 사용됨.

**수정 방안**: 각 요소에 `aria-label` 추가
```tsx
<select aria-label="접촉 유형">
<input type="date" aria-label="접촉 날짜" />
<input type="text" aria-label="접촉 내용" />
```

**확정 근거**: Read로 InlineLogInput.tsx:86-113 직접 확인

---

### [R4-1] BuyersTab Short List 에러/빈 상태 혼동 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42 (Major 70 × MEDIUM 0.6 = 42)

⚠️ 이 Major 이슈는 중간 신뢰도(MEDIUM)로 인해 P2로 분류되었습니다.

**위치**: `src/modules/ma/tabs/BuyersTab.tsx:230-238`

**문제**: API 에러 시와 데이터 없음 시 동일하게 빈 목록 표시. `isError` 상태를 추출하지 않아 사용자에게 에러 피드백 없음.

**완화 요인**: line 318-338에 에러 배너가 존재하여 부분적으로 완화됨. 다만 Short List 영역 특정 에러가 아닌 전체 에러 배너.

**수정 방안**: useShortListOverview에서 `isError` 추출 → Short List 섹션에 에러 메시지 + 재시도 버튼

**확정 근거**: Read로 BuyersTab.tsx:230-238, 318-338 확인. 에러 배너 존재하나 세분화 부족.

---

### [SEC-R4-02] LogListPopover 삭제 확인 없음 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42 (Major 70 × MEDIUM 0.6 = 42)

⚠️ 이 Major 이슈는 중간 신뢰도(MEDIUM)로 인해 P2로 분류되었습니다.

**위치**: `src/modules/ma/components/buyers/LogListPopover.tsx:67`

**문제**: 접촉 이력 삭제 시 확인 다이얼로그 없이 즉시 삭제 실행.
```tsx
onClick={() => deleteLog.mutate(log.id)}
```
대조: `ShortListOverview.tsx:118-125`는 toast 확인을 사용.

**수정 방안**: 삭제 버튼 클릭 시 확인 다이얼로그 또는 toast confirm 추가

**확정 근거**: Read로 LogListPopover.tsx:67 확인, ShortListOverview.tsx:118-125 대비 확인 절차 누락

---

### [A11Y-R4-04] BuyerFeedbackSection textarea 레이블 미연결 — [Major/HIGH] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/components/buyers/BuyerFeedbackSection.tsx`

**문제**: 피드백 입력 `<textarea>`에 `<label htmlFor>` / `id` 연결 없음. 스크린 리더가 textarea 용도를 인식 불가.

**수정 방안**: textarea에 `id="buyer-feedback"` + label에 `htmlFor="buyer-feedback"` 추가, 또는 `aria-label="의향서 피드백"` 추가

**확정 근거**: Read로 BuyerFeedbackSection.tsx 직접 확인

---

### [A11Y-R4-05] MarketingKanbanView 카드 hover/interactive 불일치 — [Major/HIGH] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/components/buyers/MarketingKanbanView.tsx`

**문제**: 칸반 카드에 `hover:shadow-md cursor-pointer` 스타일이 있으나 실제 클릭 핸들러가 없거나 `<div>`로 구현. 시각적으로 클릭 가능해 보이지만 키보드 접근 불가.

**수정 방안**: 클릭 가능 카드는 `<button>` 또는 `role="button" tabIndex={0} onKeyDown` 추가. 클릭 불필요 시 hover 스타일 제거.

**확정 근거**: Read로 MarketingKanbanView.tsx 직접 확인

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)
1. [R4-2+SEC-R4-01] [Major/HIGH]: FIRecommendModal 부분 실패 중복 제출 + 훅 우회 (점수: 80, 교차 검증됨)
2. [A11Y-R4-01] [Major/HIGH]: DartCompanyTypeahead ARIA combobox 불완전 (점수: 70)
3. [A11Y-R4-02] [Major/HIGH]: LongListFilters 접근성 레이블 누락 (점수: 70)
4. [A11Y-R4-03] [Major/HIGH]: InlineLogInput 폼 요소 레이블 누락 (점수: 70)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
5. [R4-1] [Major/MEDIUM ⚠️]: BuyersTab Short List 에러/빈 상태 혼동 (점수: 42, 신뢰도 하향됨)
6. [SEC-R4-02] [Major/MEDIUM ⚠️]: LogListPopover 삭제 확인 없음 (점수: 42, 신뢰도 하향됨)
7. [A11Y-R4-04] [Major/HIGH]: BuyerFeedbackSection textarea 레이블 미연결 (점수: 42)
8. [A11Y-R4-05] [Major/HIGH]: MarketingKanbanView 카드 hover/interactive 불일치 (점수: 42)

## 이전 라운드 제외 이슈 (미수정)

| ID | 이유 | 비고 |
|----|------|------|
| DOM-01 | MaterialTracker CIM/IM→ADVISOR_MEETING 매핑 — 비즈니스 확인 필요 | 사용자 결정 대기 |
| DUP-02 | latestStage 유틸 중복 — 별도 리팩토링 세션 | 기능 영향 없음 |

## Methodology

- **Agents**: code-reviewer, a11y-auditor, security-auditor (3개 병렬 호출)
- **Excluded Agents**: type-checker (tsc 별도 실행), api-auditor (백엔드 스코프 외), perf-auditor (성능 이슈 미탐지)
- **Files scanned**: Short List 탭 관련 15개 파일
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 전 이슈 수행 (8/8)
- **Backend availability**: 해당 없음 (프론트엔드 전용 리뷰)

## 검증 투명성

### 검증 통계
- 검증한 가설: 10건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 8건
- 거부율: 20%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 자기 수정 | 1 | SEC-R4-03: 에이전트가 스스로 확인 후 취소 |
| 신뢰도 불충분 | 1 | BuyerSummarySection formatAmountKRW — 다른 포맷 함수로 확인 |

---

> 리뷰 종료. 총 8건 이슈 (P1: 4건, P2: 4건).
