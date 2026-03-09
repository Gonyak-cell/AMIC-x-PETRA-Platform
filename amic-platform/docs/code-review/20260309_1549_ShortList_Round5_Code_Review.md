# Code Review — Short List Tab (Round 5 통합 리뷰)

> **Review Date**: 2026-03-09 15:49
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Short List 탭 구현 전체 (13개 리뷰 관점 통합)
> **Method**: Review Gates + Verified Multi-Agent Review (3 병렬 에이전트)
> **Quality Gates**: --skip-gates (Round 4에서 통과 확인)
> **Review Gates**: Backend(unavailable) Agent-Filtering(3개 에이전트 호출)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 1     | HIGH: 1                | P1: 1               |
| Moderate | 8     | HIGH: 8                | P2: 8               |
| Minor    | 6     | HIGH: 2 / MEDIUM: 3 / LOW: 1 | P3: 6       |
| **Total**| **15**| HIGH: **11** / MEDIUM: **3** / LOW: **1** | P1: **1** / P2: **8** / P3: **6** |

**FP Prevention**: 가설 22건 검증, 7건 사전 거부 (거부율: 32%)
**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용

---

## Findings

### [LS-01] BuyersTab isLoading 미추출 — [Major/HIGH] — Priority: P1

- **점수**: 70
- **파일**: `src/modules/ma/tabs/BuyersTab.tsx:56-57`
- **관점**: §2 완전성 (에러/로딩 상태)

**문제**: `useBuyers(txnId)` 훅에서 `data`만 추출하고 `isLoading`을 추출하지 않아, 데이터 로딩 중 빈 `buyers` 배열로 인해 EmptyState가 잠깐 표출된 후 데이터 도착 시 갑자기 변경됨. UX 깜박임 발생.

**증거**:
```tsx
// BuyersTab.tsx:56
const { data: buyers = [] } = useBuyers(txnId);
// isLoading 미추출 → 로딩 중 buyers=[] → EmptyState 표시
```

**수정 방안**: `isLoading` 추출 후, 로딩 중 Spinner 표시.

---

### [R5-03 / SL5-PERF-02] buyerColumns useMemo 무효화 — [Moderate/HIGH] — Priority: P2

- **점수**: 50 (교차 검증 +10)
- **파일**: `src/modules/ma/tabs/BuyersTab.tsx:94-140` (추정)
- **관점**: §4 성능 (불필요한 리렌더)

**문제**: `buyerColumns` useMemo 의존성 배열에 `updateBuyer` (useMutation 반환값)가 포함됨. React Query의 `useMutation`은 매 렌더마다 새 참조를 반환하므로, useMemo가 사실상 무효화되어 매 렌더마다 컬럼 재계산.

**수정 방안**: `updateBuyer.mutate`를 `useCallback`으로 안정화하거나, useMemo 의존성에서 제거.

---

### [R5-01] ShortListOverview logColumns 매 렌더 재생성 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/ShortListOverview.tsx`
- **관점**: §4 성능 (불필요한 재계산)

**문제**: `logColumns` 배열이 컴포넌트 함수 본문에서 매 렌더마다 새로 생성됨. useMemo 미적용.

**수정 방안**: `useMemo`로 감싸서 메모이제이션.

---

### [SL5-PERF-01] LongListFilters 검색 디바운스 미적용 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/LongListFilters.tsx`
- **관점**: §4 성능 (불필요한 리렌더)

**문제**: 검색 입력이 onChange마다 즉시 상위 컴포넌트 상태를 갱신하여 전체 리스트 리렌더 유발. 디바운스 없음.

**수정 방안**: `useDeferredValue` 또는 간단한 debounce 적용.

---

### [SL5-SEC-01] InlineLogInput content maxLength 누락 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/InlineLogInput.tsx:107-113`
- **관점**: §5 보안 (입력 검증)

**문제**: 활동 내용 텍스트 입력에 `maxLength` 제한 없음. 백엔드 검증에만 의존.

**수정 방안**: `maxLength={500}` 추가.

---

### [RES-01] FunnelKPIBar 모바일 오버플로 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/FunnelKPIBar.tsx`
- **관점**: §12 UX (반응형)

**문제**: flex 레이아웃이 모바일 뷰포트에서 오버플로. `flex-wrap` 또는 `overflow-x-auto` 미적용.

**수정 방안**: `flex-wrap` 또는 `overflow-x-auto` 추가.

---

### [SR-01 / KB-01] ShortListOverview BuyerRow 접근성 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/ShortListOverview.tsx`
- **관점**: §5 접근성 (키보드/스크린리더)

**문제**: BuyerRow의 스테이지 셀 클릭 시 Popover 열리나, `aria-label`과 `aria-controls` 미설정. 스크린리더가 버튼 역할을 인식하기 어려움.

**수정 방안**: 스테이지 셀 버튼에 `aria-label` 및 `aria-expanded` 추가.

---

### [SR-02] MarketingStageTracker full 모드 접근성 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/MarketingStageTracker.tsx`
- **관점**: §5 접근성

**문제**: full 모드에서 각 단계 원형 아이콘에 `aria-label` 없음. 스크린리더가 단계 상태를 전달할 수 없음.

**수정 방안**: 각 단계 아이콘에 `aria-label={`${label} ${completed ? '완료' : '미완료'}`}` 추가.

---

### [KB-02] LogListPopover 포커스 트래핑 — [Moderate/HIGH] — Priority: P2

- **점수**: 40
- **파일**: `src/modules/ma/components/buyers/LogListPopover.tsx` → `src/components/ui/Popover.tsx`
- **관점**: §5 접근성 (키보드)

**문제**: Popover 컴포넌트에 포커스 트래핑 미구현. Tab 키로 Popover 밖으로 포커스 이탈 가능.

**수정 방안**: `Popover` 공통 컴포넌트에 포커스 트래핑 로직 추가 (별도 이슈로 분리 권장).

---

### [R5-04] BUYER_STATUS_OPTIONS "전체" 옵션 누락 — [Minor/HIGH] — Priority: P3

- **점수**: 24 (확인: `SELECT_ACTIVE` 등은 있으나 빈 값 "전체" 미포함)
- **파일**: `src/modules/ma/constants/buyer.ts`
- **관점**: §12 UX (필터링)

**수정 방안**: `{ value: "", label: "전체" }` 옵션 추가.

---

### [FV-02] LongListFilters 검색 Input aria-label 누락 — [Minor/HIGH] — Priority: P3

- **점수**: 20
- **파일**: `src/modules/ma/components/buyers/LongListFilters.tsx`
- **관점**: §5 접근성

**수정 방안**: `aria-label="회사명 검색"` 추가.

---

### [R5-02] BuyerSummarySection formatAmountKRW 중복 — [Minor/MEDIUM] — Priority: P3

- **점수**: 20
- **파일**: `src/modules/ma/components/buyers/BuyerSummarySection.tsx`
- **관점**: §9 코드중복

**문제**: `formatKRW` 유틸과 유사한 포맷 로직이 컴포넌트 내에 인라인으로 존재.

**수정 방안**: 기존 `formatKRW` 유틸 사용으로 통합.

---

### [R5-08] ShortListOverview logForm UTC 날짜 — [Minor/MEDIUM] — Priority: P3

- **점수**: 12
- **파일**: `src/modules/ma/components/buyers/ShortListOverview.tsx`
- **관점**: §3 안정성 (시간대)

**문제**: `new Date().toISOString().slice(0,10)` 사용 — UTC 기준이므로 한국 시간 자정 전후 날짜 불일치 가능.

**수정 방안**: `InlineLogInput`의 `todayStr()` 패턴(로컬 시간 기반) 사용.

---

### [R5-09] DartMetric format 불일치 — [Minor/MEDIUM] — Priority: P3

- **점수**: 12
- **파일**: `src/modules/ma/components/buyers/DartMetric.tsx`
- **관점**: §10 네이밍/일관성

**문제**: 독자적 숫자 포맷 로직 사용, `formatKRW` 유틸과 불일치.

**수정 방안**: 공통 포맷 유틸 사용 검토 (비즈니스 로직 확인 필요).

---

### [R5-07] BuyerDetailPanel 스크롤 타이밍 — [Minor/LOW] — Priority: P3

- **점수**: 12
- **파일**: `src/modules/ma/components/buyers/BuyerDetailPanel.tsx`
- **관점**: §12 UX

**문제**: buyer 변경 시 패널 내용이 변경되나 스크롤 위치가 리셋되지 않아, 이전 buyer의 스크롤 위치에서 새 buyer 정보가 보일 수 있음.

**수정 방안**: `useEffect`로 buyer 변경 시 `scrollTop = 0` 리셋.

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. [LS-01] [Major/HIGH]: BuyersTab isLoading 미추출 → EmptyState 깜박임 (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. [R5-03/SL5-PERF-02] [Moderate/HIGH]: buyerColumns useMemo 무효화 (점수: 50, 교차 검증)
2. [R5-01] [Moderate/HIGH]: ShortListOverview logColumns 매 렌더 재생성 (점수: 40)
3. [SL5-PERF-01] [Moderate/HIGH]: LongListFilters 검색 디바운스 (점수: 40)
4. [SL5-SEC-01] [Moderate/HIGH]: InlineLogInput content maxLength 누락 (점수: 40)
5. [RES-01] [Moderate/HIGH]: FunnelKPIBar 모바일 오버플로 (점수: 40)
6. [SR-01/KB-01] [Moderate/HIGH]: ShortListOverview BuyerRow 접근성 (점수: 40)
7. [SR-02] [Moderate/HIGH]: MarketingStageTracker full 모드 접근성 (점수: 40)
8. [KB-02] [Moderate/HIGH]: LogListPopover 포커스 트래핑 (점수: 40)

### P3 — 저우선 (점수: <30)
1. [R5-04] [Minor/HIGH]: BUYER_STATUS_OPTIONS "전체" 옵션 누락 (점수: 24)
2. [FV-02] [Minor/HIGH]: LongListFilters 검색 aria-label 누락 (점수: 20)
3. [R5-02] [Minor/MEDIUM]: BuyerSummarySection formatAmountKRW 중복 (점수: 20)
4. [R5-08] [Minor/MEDIUM]: ShortListOverview logForm UTC 날짜 (점수: 12)
5. [R5-09] [Minor/MEDIUM]: DartMetric format 불일치 (점수: 12)
6. [R5-07] [Minor/LOW]: BuyerDetailPanel 스크롤 타이밍 (점수: 12)

## Excluded Issues (이전 라운드에서 제외 결정)

- **DOM-01**: Kanban DnD 미구현 — 비즈니스 확인 필요 (별도 이슈)
- **DUP-02**: stageMap 중복 로직 — 별도 리팩토링 이슈
- **KB-02**: Popover 포커스 트래핑 — 공통 컴포넌트 변경 필요 (별도 이슈 권장)

## Methodology

- Agents: code-reviewer, a11y-auditor, perf-auditor (3 병렬)
- Files scanned: Short List 탭 구현 전체 (~25개 파일)
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: R5-03 + SL5-PERF-02 교차 확인 → 동일 이슈 병합

## 검증 투명성

### 검증 통계
- 검증한 가설: 22건
- 거부된 가설 (사전 제거): 7건
- 보고된 이슈: 15건
- 거부율: 32%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | "에러 처리 없음" → Read로 이미 구현 확인 |
| 이미 수정됨 | 2 | Round 4에서 수정된 이슈 재보고 |
| 중복 | 1 | R5-03 = SL5-PERF-02 동일 이슈 |
| 범위 외 | 1 | Popover 공통 컴포넌트 — Short List 전용 아님 |
