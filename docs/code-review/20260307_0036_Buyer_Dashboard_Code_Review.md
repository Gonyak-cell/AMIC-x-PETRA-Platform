# Code Review — 잠재매수인 커뮤니케이션 대시보드

> **Review Date**: 2026-03-07 00:36
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Phase 1~4 Buyer Dashboard — 신규 9개 + 수정 2개 파일
> **Method**: Quality Gates + Verified Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS*) eslint(N/A) build(PASS)
> **\*중요**: `npx tsc --noEmit`(root)은 PASS이나, `npx tsc --noEmit --project tsconfig.app.json`은 **5건 에러**. Root tsconfig의 `"files": []` 설정으로 실제 타입 검사가 수행되지 않는 구조적 문제 발견.

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2                | P0: 2                |
| Major    | 3     | HIGH: 3                | P1: 3                |
| Moderate | 4     | HIGH: 3 / MEDIUM: 1    | P2: 4                |
| Minor    | 2     | HIGH: 1 / LOW: 1       | P3: 2                |
| **Total**| **11** | HIGH: **9** / MEDIUM: **1** / LOW: **1** | P0: **2** / P1: **3** / P2: **4** / P3: **2** |

**FP Prevention**: 가설 14건 검증, 3건 사전 거부 (거부율: 21%)
**Cross-Verification**: Critical + Major 5건 모두 코드 Read로 확인 (CONFIRMED: 5건)

---

## Findings

### P0 — 즉시 수정 (보안/데이터 무결성/런타임 크래시)

#### [C1] MarketingStageTracker에 잘못된 prop 전달 — [Critical/HIGH] — Priority: P0 (점수: 100)

**위치**: [ShortListMasterList.tsx:74](amic-platform/src/modules/ma/components/buyers/ShortListMasterList.tsx#L74)

**문제**: `MarketingStageTracker`는 `summary: BuyerStageSummary` prop을 필수로 기대하지만, `overviewData={[summary]}`로 잘못된 prop명으로 전달.

```tsx
// 현재 (잘못됨)
<MarketingStageTracker compact overviewData={[summary]} />

// 올바른 코드
<MarketingStageTracker compact summary={summary} />
```

**영향**: 런타임에서 `summary.stages[s]` 접근 시 `TypeError: Cannot read properties of undefined` 크래시. Short List에서 buyer를 선택하면 앱이 중단됨.

**검증**:
- MarketingStageTracker.tsx:14-17 — `interface MarketingStageTrackerProps { summary: BuyerStageSummary; compact?: boolean; }`
- `npx tsc --project tsconfig.app.json` 실행 시 TS2322 에러 정확히 탐지됨
- `npx tsc --noEmit` (root tsconfig)에서는 미탐지 — root tsconfig의 `"files": []` 때문

**신뢰도**: HIGH (코드 직접 확인 + tsc 에러 재현)

---

#### [C2] tsc 검증 명령어 구조적 문제 — [Critical/HIGH] — Priority: P0 (점수: 100)

**위치**: tsconfig.json (root)

**문제**: Root `tsconfig.json`이 `"files": []`와 `references`로 구성되어 있어, `npx tsc --noEmit` 실행 시 **아무 파일도 검사하지 않음**. 실제 타입 체크는 `npx tsc --noEmit --project tsconfig.app.json`으로 실행해야 함.

```json
// tsconfig.json (root) — 파일 포함 없음
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

**영향**: CI 및 수동 검증에서 `npx tsc --noEmit`을 사용하면 타입 에러가 모두 통과됨. 현재 5건의 실제 타입 에러가 숨겨져 있음:
1. ShortListMasterList.tsx:74 — TS2322 (overviewData prop)
2. BuyerSummarySection.tsx:85 — TS2322 (size prop)
3. BuyerMeetingTimeline.tsx:87,90,91 — TS7053 (any 타입 인덱싱) x3

**수정 방향**: `npx tsc -b --noEmit` (build mode) 또는 `npx tsc --noEmit -p tsconfig.app.json` 사용

**신뢰도**: HIGH (직접 재현)

---

### P1 — 스프린트 우선 (안정성/정확성)

#### [M1] `allBuyers` 불안정 참조로 useMemo 무효화 — [Major/HIGH] — Priority: P1 (점수: 70)

**위치**: [BuyersTab.tsx:237,257](amic-platform/src/modules/ma/tabs/BuyersTab.tsx#L237)

**문제**: `const allBuyers = buyers ?? []`가 매 렌더마다 새 배열 참조를 생성하여 `useMemo` deps가 무효화됨. `filteredBuyers`, `selectedBuyer`, `selectedStageSummary` 3개의 useMemo가 모두 영향받음.

```tsx
// 현재 (매 렌더마다 새 [] 참조)
const allBuyers = buyers ?? [];
const filteredBuyers = useMemo(() => { ... }, [allBuyers, longListFilters]);

// 수정
const allBuyers = useMemo(() => buyers ?? [], [buyers]);
```

**신뢰도**: HIGH

---

#### [M2] BuyerFeedbackSection — buyer 전환 시 notes 미동기화 — [Major/HIGH] — Priority: P1 (점수: 70)

**위치**: [BuyerFeedbackSection.tsx:18](amic-platform/src/modules/ma/components/buyers/BuyerFeedbackSection.tsx#L18)

**문제**: `useState(buyer.notes ?? "")`는 최초 마운트 시만 초기화. SlidePanel에서 다른 buyer를 선택하면 이전 buyer의 notes가 그대로 표시됨.

```tsx
// 현재 — buyer가 바뀌어도 notes는 이전 값 유지
const [notes, setNotes] = useState(buyer.notes ?? "");
```

**수정 방향**: 부모에서 `key={buyer.id}`를 지정하거나 `useEffect`로 동기화.

**신뢰도**: HIGH

---

#### [M3] MaterialTracker — "CIM/IM 발송"이 ADVISOR_MEETING에 잘못 매핑 — [Major/HIGH] — Priority: P1 (점수: 70)

**위치**: [MaterialTracker.tsx:43-45](amic-platform/src/modules/ma/components/buyers/MaterialTracker.tsx#L43)

**문제**: "CIM/IM 발송" 라벨에 `ADVISOR_MEETING` stage를 매핑. `ADVISOR_MEETING`은 "자문사 미팅"으로 정의되어 있어 비즈니스 로직 불일치.

```tsx
{
  label: "CIM/IM 발송",
  done: stages?.ADVISOR_MEETING != null,  // ADVISOR_MEETING = "자문사 미팅" (불일치)
  date: stages?.ADVISOR_MEETING ?? null,
},
```

**신뢰도**: HIGH (buyer.ts:54의 상수 정의와 대조)

---

### P2 — 개선 권장 (코드 품질)

#### [Md1] FunnelKPIBar — 반복 필터링에 useMemo 없음 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**위치**: [FunnelKPIBar.tsx:42-64](amic-platform/src/modules/ma/components/buyers/FunnelKPIBar.tsx#L42)

**문제**: `steps` 배열이 매 렌더마다 `buyers.filter()`를 5회 호출. `useMemo`로 감싸면 불필요한 반복 계산 방지.

---

#### [Md2] BuyerSummarySection — Badge `size` prop 미존재 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**위치**: [BuyerSummarySection.tsx:85](amic-platform/src/modules/ma/components/buyers/BuyerSummarySection.tsx#L85)

**문제**: `<Badge variant="neutral" size="sm">` — Badge 컴포넌트에 `size` prop이 없음. tsc TS2322 에러.

**신뢰도**: HIGH (tsc --project tsconfig.app.json에서 에러 확인)

---

#### [Md3] LongListFilters — BUYER_STATUS_OPTIONS에 "전체" 옵션 없음 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**위치**: [LongListFilters.tsx:55-58](amic-platform/src/modules/ma/components/buyers/LongListFilters.tsx#L55)

**문제**: 타입/Tier 필터에는 `{ value: "", label: "전체" }` 옵션이 있으나 상태 필터에는 없어 선택 후 초기화 불가.

---

#### [Md4] BuyerSummarySection — `rounded-dr` 오타 가능성 — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

**위치**: [BuyerSummarySection.tsx:162](amic-platform/src/modules/ma/components/buyers/BuyerSummarySection.tsx#L162)

**문제**: `rounded-dr`은 Tailwind CSS 표준 클래스가 아님. `rounded` 또는 `rounded-br` 의도 가능성.

---

### P3 — 저우선 (개선 가능)

#### [m1] showBuyerModal 열기 트리거 없음 — [Minor/HIGH] — Priority: P3 (점수: 20)

**위치**: [BuyersTab.tsx:115,441-526](amic-platform/src/modules/ma/tabs/BuyersTab.tsx#L115)

**문제**: `showBuyerModal` state와 Modal이 정의되어 있으나 열기 트리거가 JSX에 없음. FI/SI 자동 추천으로 대체된 dead code 가능성.

---

#### [m2] DD_STATUSES에 BID_SUBMITTED 누락 — [Minor/LOW] — Priority: P3 (점수: 6)

**위치**: [FunnelKPIBar.tsx:34-40](amic-platform/src/modules/ma/components/buyers/FunnelKPIBar.tsx#L34)

**문제**: `DD_STATUSES`에 `BID_SUBMITTED`가 없음. 비즈니스 의도 확인 필요.

---

## tsc --project tsconfig.app.json 미해결 에러 (5건)

| # | 파일 | 에러 코드 | 설명 |
|---|------|----------|------|
| 1 | ShortListMasterList.tsx:74 | TS2322 | overviewData prop 미존재 (= C1) |
| 2 | BuyerSummarySection.tsx:85 | TS2322 | size prop 미존재 (= Md2) |
| 3 | BuyerMeetingTimeline.tsx:87 | TS7053 | any 타입으로 Record 인덱싱 |
| 4 | BuyerMeetingTimeline.tsx:90 | TS7053 | any 타입으로 Record 인덱싱 |
| 5 | BuyerMeetingTimeline.tsx:91 | TS7053 | any 타입으로 Record 인덱싱 |

---

## Priority Matrix

| Priority | 건수 | 즉시 수정 필요 |
|----------|------|---------------|
| **P0** | 2건 | C1 (런타임 크래시), C2 (tsc 검증 누락) |
| **P1** | 3건 | M1 (useMemo 무효화), M2 (데이터 오염), M3 (비즈니스 로직 불일치) |
| **P2** | 4건 | 성능/타입/UX 개선 |
| **P3** | 2건 | dead code, 퍼널 정의 확인 |

---

## Methodology

- **Agents**: superpowers:code-reviewer (전체 코드 품질), dependency-checker (의존성 교차 확인)
- **Files scanned**: 11개 (신규 9 + 수정 2)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 5건 전체 Read 확인 → CONFIRMED 5건
- **Key Discovery**: `npx tsc --noEmit` (root tsconfig)이 실제 타입 검사를 수행하지 않는 구조적 문제 발견. `--project tsconfig.app.json` 필수.

## 검증 투명성

### 검증 통계
- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 3건
- 보고된 이슈: 11건
- 거부율: 21%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | collaboration.ts buyer 타입 추가 — 정합성 확인됨 |
| 의도적 설계 | 1 | InterestIndicator NOT_TARGET 미처리 — 의도적 가능성 높아 Moderate로 하향 |
| 중복 | 1 | BuyerMeetingTimeline tsc 에러 — C2에서 통합 보고 |
