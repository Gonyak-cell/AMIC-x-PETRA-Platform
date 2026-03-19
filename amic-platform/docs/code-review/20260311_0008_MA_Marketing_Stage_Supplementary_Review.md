# Code Review — MA Marketing Stage 8단계 재구성 보충 리뷰

> **Review Date**: 2026-03-11 00:08
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff HEAD` — 8개 파일 (FE 6 + BE 2) + 마이그레이션/서비스 확장 검토
> **Method**: Quality Gates + Review Gates + Verified Multi-Agent Review (5 agents) + Cross-Verification
> **Quality Gates**: tsc(PASS) ruff-check(PASS) ruff-format(PASS) pytest(PASS, 19/19)
> **Review Gates**: Backend(deal-mgmt available) Agent-Filtering(5개 에이전트 호출, 0개 제외)
> **Severity Filter**: Major 이상만 보고

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 13    | HIGH: 8 / MEDIUM: 5 | P1: 8 / P2: 5 |
| **Total**| **13** | HIGH: **8** / MEDIUM: **5** | P1: **8** / P2: **5** |

**FP Prevention**: 가설 18건 검증, 5건 사전 거부 (거부율: 28%)
**Cross-Verification**: R2 → PARTIAL (신뢰도 하향), R3/M1 → CONFIRMED

---

## Findings

### [R3] ADVANCE_PATH에 DD_IN_PROGRESS 이후 경로 누락 — [Major/HIGH] — Priority: P1

**File**: buyer_status_service.py:31-41
**Score**: 70 (70 x 1.0)

**Evidence**:
```python
ADVANCE_PATH: dict[BuyerCandidateStatus, BuyerCandidateStatus] = {
    _S.IDENTIFIED: _S.CONTACTED,
    ...
    _S.DD_GRANTED: _S.DD_IN_PROGRESS,
    # DD_IN_PROGRESS 이후 경로 없음
}
```

**Issue**: `DD_IN_PROGRESS`(ordinal 9) 이후 `LOI_RECEIVED`(ordinal 10) 이하 경로가 누락. 마케팅 스테이지 LOI_RECEIVED 로그 시 목표 buyer status는 `LOI_RECEIVED`(ordinal 10)이지만, ADVANCE_PATH에서 `DD_IN_PROGRESS` 키가 없어 while 루프가 즉시 break.

**Impact**: LOI 접수, LOI 승인, 최종 선정, 입찰 제출 단계로의 자동 승격이 모두 불가. 수동으로만 buyer status 변경 가능.

**Suggestion**:
```python
_S.DD_IN_PROGRESS: _S.LOI_RECEIVED,
_S.LOI_RECEIVED: _S.LOI_ACCEPTED,
_S.LOI_ACCEPTED: _S.SELECTED,
_S.SELECTED: _S.BID_SUBMITTED,
```

**Cross-Verification**: CONFIRMED — `STATUS_ORDER` 확인: DD_IN_PROGRESS=9, LOI_RECEIVED=10. `auto_advance_buyer_status` 87행 while 조건에서 9 < 10이므로 루프 진입하나, `ADVANCE_PATH.get(DD_IN_PROGRESS)` = None으로 즉시 break.

---

### [M1] buyer_export_service.py의 _STAGE_LABELS가 구 MarketingStage 값 참조 — [Major/HIGH] — Priority: P1

**File**: buyer_export_service.py:63-70
**Score**: 70 (70 x 1.0)

**Evidence**:
```python
_STAGE_LABELS: dict[str, str] = {
    "IDENTIFIED": "발굴",
    "EMAIL_SENT": "이메일 발송",        # 삭제된 enum
    "PHONE_CALL": "전화 접촉",          # 삭제된 enum
    "ADVISOR_MEETING": "어드바이저 미팅", # 삭제된 enum
    "NDA_SIGNED": "NDA 체결",
    "TARGET_MEETING": "대상회사 미팅",    # 삭제된 enum
}
```

**Issue**: 마이그레이션 079 이후 삭제된 4개 enum의 라벨이 남아있고, 신규 6개 enum의 라벨이 누락.

**Impact**: Excel export 시 신규 마케팅 스테이지의 한글 라벨이 누락되어 영문 코드명이 그대로 출력됨.

**Cross-Verification**: CONFIRMED — 파일 직접 Read로 63-70행 확인.

---

### [R1] TimelineView와 GridView 간 진행률 계산 불일치 — [Major/HIGH] — Priority: P1

**File**: MarketingTimelineView.tsx:103
**Score**: 70 (70 x 1.0)

**Evidence**:
```tsx
// TimelineView:103 — 인덱스 기반
Math.round(((currentIdx + 1) / effectiveStageCount(stages)) * 100)

// GridView:155 — 완료 카운트 기반
Math.round((completedCount / effectiveTotal) * 100)
```

**Issue**: GridView는 `countCompletedStages()`로 실제 완료 수를, TimelineView는 `latestCompletedStageIndex() + 1`로 최고 인덱스+1을 분자로 사용. 비순차 완료 시(예: IDENTIFIED + NDA_SIGNED 완료, TEASER_SENT 미완료) GridView는 2/7=29%, TimelineView는 3/7=43%로 표시됨.

**Impact**: 같은 매수자의 진행률이 뷰 전환 시 달라져 사용자 혼란.

**Suggestion**: TimelineView도 `countCompletedStages(stages) / effectiveStageCount(stages)` 사용.

---

### [A11Y-1] CircularProgress SVG에 접근 가능한 이름 없음 — [Major/HIGH] — Priority: P1

**File**: MarketingGridView.tsx:38
**Score**: 70 (70 x 1.0)

**Evidence**:
```tsx
<svg width="28" height="28" viewBox="0 0 28 28" className="block">
```

**Issue**: SVG에 `role="img"`, `aria-label`, `<title>` 모두 없음. 스크린리더가 진행률 정보를 전달할 수 없음.

**Suggestion**: `<svg ... role="img" aria-label={진행률 ${label}}>` 추가.

---

### [A11Y-2] Timeline role="list" 컨테이너에 role="listitem" 자식 없음 — [Major/HIGH] — Priority: P1

**File**: MarketingTimelineView.tsx:183-296
**Score**: 70 (70 x 1.0)

**Evidence**:
```tsx
<div className="relative ml-1.5" aria-label="마케팅 진행 타임라인" role="list">
  {timelineItems.map((item, idx) => {
    return (
      <div key={...} className="flex items-start gap-3 relative">
      // role="listitem" 누락
```

**Issue**: ARIA 명세상 `role="list"` 컨테이너는 `role="listitem"` 자식만 포함해야 함.

**Suggestion**: 각 직접 자식 div에 `role="listitem"` 추가.

---

### [PERF-1] ShortListSummaryBar KPI 계산에 useMemo 누락 — [Major/HIGH] — Priority: P1

**File**: ShortListSummaryBar.tsx:27-31
**Score**: 70 (70 x 1.0)

**Evidence**:
```tsx
const dropCount = buyers.filter((b) => b.status === "BID_DROPPED").length;
const activeCount = buyers.length - dropCount;
const ndaCount = overviewData.filter((s) => s.stages.NDA_SIGNED).length;
const loiCount = overviewData.filter((s) => s.stages.LOI_RECEIVED).length;
const tier1Count = buyers.filter((b) => b.tier === "TIER_1").length;
```

**Issue**: 5개 `.filter()` 호출이 `useMemo` 없이 렌더 본문에 직접 위치. 같은 파일 33행의 `avgPct`는 `useMemo`로 보호되어 있어 비일관적.

**Suggestion**: 하나의 `useMemo` 블록에서 모든 KPI를 한 번의 순회로 계산.

---

### [UX-1] TimelineView 미팅 데이터 로딩 중 로딩 상태 표시 없음 — [Major/HIGH] — Priority: P1

**File**: MarketingTimelineView.tsx:38-40
**Score**: 70 (70 x 1.0)

**Evidence**:
```tsx
const { data: meetingData, isError: meetingError } = useMeetingLogs(txnId, {
  meetingPhase: "MARKETING",
});
```

**Issue**: `isLoading`/`isPending`을 구조 분해하지 않음. 미팅 데이터 fetch 중 "미팅 없는 상태"와 "로딩 중"이 구분 불가.

**Suggestion**: `isPending`을 구조 분해하고 로딩 인디케이터 표시.

---

### [R2] ShortListSummaryBar KPI 카운트에 buyers 교차 필터링 없음 — [Major/MEDIUM] — Priority: P2

**File**: ShortListSummaryBar.tsx:29-30
**Score**: 42 (70 x 0.6)

**Issue**: `overviewData`와 `buyers` 배열의 ID 교차 검증 없이 KPI 카운트. API가 이미 short list 필터링하므로 실제 발생 가능성은 낮음.

> 이 Major 이슈는 중간 신뢰도(MEDIUM)로 인해 P2로 분류되었습니다.

---

### [R4] effectiveStageCount 0-division 방어 코드 없음 — [Major/MEDIUM] — Priority: P2

**File**: ShortListSummaryBar.tsx:42
**Score**: 42 (70 x 0.6)

**Issue**: SKIPPABLE_STAGES 확장 시 `effectiveStageCount`가 0 반환 가능. 현재 SKIPPABLE이 1개뿐이므로 최소 7 반환, 실질적 위험 없음.

> 이 Major 이슈는 중간 신뢰도(MEDIUM)로 인해 P2로 분류되었습니다.

---

### [A11Y-3] 미완료 셀의 색상 전용 상태 구분 — [Major/MEDIUM] — Priority: P2

**File**: MarketingGridCell.tsx:84-98
**Score**: 42 (70 x 0.6)

**Issue**: 비완료 셀이 6px 회색 점으로만 표시. 완료 셀의 체크 아이콘과 크기 차이(w-5 vs w-1.5)로 부분 완화됨. WCAG 1.4.1 Use of Color.

---

### [TS-1] as Partial<Record<...>> 타입 단언 — [Major/MEDIUM] — Priority: P2

**File**: MarketingTimelineView.tsx:63
**Score**: 42 (70 x 0.6)

**Issue**: 빈 객체를 `as`로 캐스팅. 런타임 안전하나 타입 검사 우회.

**Suggestion**: `const EMPTY_STAGES: Partial<Record<MarketingStage, string | null>> = {}` 상수 정의.

---

### [PERF-2] MarketingGridView 행별 연산 렌더마다 재실행 — [Major/MEDIUM] — Priority: P2

**File**: MarketingGridView.tsx:148-162
**Score**: 42 (70 x 0.6)

**Issue**: `sorted.map()` 내에서 buyer당 3개 유틸 함수 호출. 200명 기준 매 렌더 4800회 비교. `sorted`는 `useMemo`로 보호되나 `.map()` 내부 연산은 보호 안 됨.

---

### [PERF-3] MarketingTimelineView 인라인 연산 렌더마다 재실행 — [Major/MEDIUM] — Priority: P2

**File**: MarketingTimelineView.tsx:98-134
**Score**: 42 (70 x 0.6)

**Issue**: buyer당 `Set` 생성 + `filter()` + `buildTimelineItems()` 호출. PERF-2보다 무거운 연산이 매 렌더마다 반복.

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. [R3] [Major/HIGH]: ADVANCE_PATH DD_IN_PROGRESS 이후 경로 누락 — buyer_status_service.py (70)
2. [M1] [Major/HIGH]: 구 MarketingStage 라벨 잔존 — buyer_export_service.py (70)
3. [R1] [Major/HIGH]: TimelineView/GridView 진행률 불일치 — MarketingTimelineView.tsx (70)
4. [A11Y-1] [Major/HIGH]: SVG 접근 가능한 이름 없음 — MarketingGridView.tsx (70)
5. [A11Y-2] [Major/HIGH]: role="listitem" 누락 — MarketingTimelineView.tsx (70)
6. [PERF-1] [Major/HIGH]: KPI useMemo 누락 — ShortListSummaryBar.tsx (70)
7. [UX-1] [Major/HIGH]: 미팅 로딩 상태 없음 — MarketingTimelineView.tsx (70)

### P2 — 개선 권장 (점수: 30-59)
1. [R2] [Major/MEDIUM]: KPI 교차 필터링 없음 — ShortListSummaryBar.tsx (42)
2. [R4] [Major/MEDIUM]: 0-division 방어 없음 — ShortListSummaryBar.tsx (42)
3. [A11Y-3] [Major/MEDIUM]: 색상 전용 상태 구분 — MarketingGridCell.tsx (42)
4. [TS-1] [Major/MEDIUM]: as 타입 단언 — MarketingTimelineView.tsx (42)
5. [PERF-2] [Major/MEDIUM]: GridView 행별 연산 — MarketingGridView.tsx (42)
6. [PERF-3] [Major/MEDIUM]: TimelineView 인라인 연산 — MarketingTimelineView.tsx (42)

---

## Methodology

- **Agents**: code-reviewer, security-auditor, api-auditor, a11y-auditor, type-checker, migration-validator, performance-auditor, ux-auditor
- **Files scanned**: 8 (diff) + 3 (확장 검토: buyer_export_service.py, enums.py, 079 migration)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: R3, M1 CONFIRMED; R2 PARTIAL (신뢰도 하향)

## 검증 투명성

### 검증 통계
- 검증한 가설: 18건
- 거부된 가설 (사전 제거): 5건
- 보고된 이슈: 13건
- 거부율: 28%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 2 | XSS 가설 — React 자동 이스케이핑 확인 |
| 이미 수정됨 | 1 | WCAG 색상 대비 — 이전 세션에서 bg-green-700 수정 완료 |
| 신뢰도 불충분 | 1 | Rate limiting 가설 — 이미 구현 확인 |
| 범위 외 | 1 | FDD/KIIS 백엔드 관련 가설 — 스코프 외 |

### 이전 리뷰 대비 신규 발견

이전 리뷰(20260310_2337)에서 미커버된 관점:
- **마이그레이션 데이터 무결성** (M1): buyer_export_service.py 구 라벨 — 이전 스코프 외
- **자동 승격 경로 완전성** (R3): ADVANCE_PATH 후반부 경로 체인 미검토
- **뷰 간 진행률 일관성** (R1): 교차 비교 미수행
- **UX 로딩 상태** (UX-1): 미팅 데이터 로딩 인디케이터 미커버
- **성능 최적화** (PERF-1~3): useMemo 일관성 미커버
