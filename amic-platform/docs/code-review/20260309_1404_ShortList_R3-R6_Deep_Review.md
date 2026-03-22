# Code Review — Short List 탭 R3~R6 심층 리뷰

> **Review Date**: 2026-03-09 14:04
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Short List 탭 구현 파일 — R3(데이터 무결성), R4(에러 처리), R5(성능/의존성), R6(도메인 로직/테스트/복잡도)
> **Method**: Review Gates(skip) + Verified Multi-Agent Review (3 에이전트 병렬) + Cross-Verification
> **Quality Gates**: --skip-gates (이전 세션에서 tsc/eslint 통과 확인)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | —                      | —                    |
| Major    | 14    | HIGH: 10 / MEDIUM: 4 / LOW: 0 | P1: 10 / P2: 4 |
| Moderate | 0     | —                      | —                    |
| Minor    | 0     | —                      | —                    |
| **Total**| **14**| HIGH: **10** / MEDIUM: **4** / LOW: **0** | P1: **10** / P2: **4** |

**FP Prevention**: 가설 20건 검증, 3건 중복 병합, 3건 교차 검증 보너스
**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용 — MEDIUM 이슈 4건 P2로 하향

---

## Findings

### [R3-002] REJECTED 상태가 NDA/CIM/DD 3개 Set에 모두 포함 — Funnel KPI 중복 카운트 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/components/buyers/FunnelKPIBar.tsx:15-30`
**교차 검증**: ✅ R6-002와 동일 이슈 — 2개 에이전트 확인

**증거**:
```tsx
const NDA_AND_AFTER = new Set(["NDA_SIGNED", "NDA_REJECTED", "CIM_SENT", ..., "REJECTED", ...]);
const CIM_AND_AFTER = new Set(["CIM_SENT", ..., "REJECTED", ...]);
const DD_STATUSES   = new Set(["DD_GRANTED", ..., "REJECTED", ...]);
```

**문제**: REJECTED 바이어가 NDA, CIM, DD 3개 퍼널 단계에 모두 카운트됨. 실제로는 마지막 활성 단계에서만 카운트되어야 함.
- 예: NDA 단계에서 REJECTED된 바이어가 DD 단계에도 카운트
- 퍼널 전환율이 왜곡됨

**수정 방향**: REJECTED 바이어는 마지막 활성 단계(rejected_at_stage 또는 이전 상태 이력 기반)에서만 카운트하거나, REJECTED를 별도 카테고리로 분리

**점수**: 70 × 1.0 + 10(교차) = **80**

---

### [R4-002] mutation onError 핸들러가 백엔드 에러 상세를 무시 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/hooks/useMarketingLogs.ts` (3개 mutation), `src/modules/ma/hooks/useTransactions.ts` (5개 mutation)
**증거**:
```tsx
// useMarketingLogs.ts — 3개 mutation 모두 동일 패턴
onError: () => { toast.error("마케팅 로그 저장에 실패했습니다."); }

// useTransactions.ts:67-69 — 동일 패턴
onError: () => { toast.error("딜 생성에 실패했습니다."); }
```

**대조 (올바른 패턴)**:
```tsx
// useAdvancePhase.ts — err.message 활용
onError: (err: Error) => { toast.error(err.message || "단계 진행에 실패했습니다."); }
```

**문제**: 8개 mutation에서 백엔드 에러 상세(validation 실패, 권한 오류, 409 충돌 등)가 사용자에게 전달되지 않음. 디버깅 어려움.

**수정 방향**: `onError: (err: Error) => toast.error(err.message || "기본 메시지")` 패턴으로 통일

**점수**: 70 × 1.0 = **70**

---

### [R4-003] Short List 컴포넌트 트리에 ErrorBoundary 없음 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/tabs/BuyersTab.tsx` (Short List 영역)

**증거**: `BuyersTab.tsx` 전체에서 ErrorBoundary 래핑 없음. Grid/Kanban/Timeline 뷰가 렌더링 에러 발생 시 전체 MA 페이지 크래시.

**문제**: 하위 컴포넌트(MarketingGridView, MarketingKanbanView, MarketingTimelineView)에서 렌더링 에러 발생 시 에러가 상위로 전파되어 전체 탭 또는 페이지가 화이트 스크린으로 변함.

**수정 방향**: Short List 뷰 영역을 ErrorBoundary로 래핑, 에러 시 폴백 UI + 재시도 버튼 제공

**점수**: 70 × 1.0 = **70**

---

### [R4-004] 에러 배너가 flex 헤더 내부에서 레이아웃 깨짐 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/tabs/BuyersTab.tsx:~130-145`

**증거**:
```tsx
<div className="flex items-center justify-between ...">
  <h3>Short List</h3>
  {/* 에러 배너가 flex row 안에 위치 */}
  {isErrorShortList && <div className="bg-red-50 ...">에러 메시지</div>}
  <ViewToggle />
</div>
```

**문제**:
1. 에러 배너가 `flex items-center` 행 내부에 있어 헤더와 같은 줄에 표시됨
2. 여러 에러 소스(buyers, overview) 중 하나만 표시 가능
3. 좁은 화면에서 헤더 레이아웃 깨짐

**수정 방향**: 에러 배너를 헤더 아래 별도 행으로 이동, 복수 에러 소스 지원

**점수**: 70 × 1.0 = **70**

---

### [R5-001] 개발용 Mock 데이터가 프로덕션 번들에 포함 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/constants/devMockBuyers.ts`

**증거**: `DEV_MOCK_BUYERS`, `DEV_MOCK_OVERVIEW` 배열이 상수 파일로 정의되어 있으며, `BuyersTab.tsx`에서 조건부로 사용:
```tsx
import { DEV_MOCK_BUYERS, DEV_MOCK_OVERVIEW } from "../constants/devMockBuyers";
// ...
const realShortList = buyers?.filter(b => b.is_short_listed) ?? [];
const displayBuyers = realShortList.length > 0 ? realShortList : DEV_MOCK_BUYERS;
```

**문제**: `import`가 정적이므로 mock 데이터가 항상 번들에 포함됨. 프로덕션에서 불필요한 번들 크기 증가. 실제 데이터가 빈 배열일 때 mock 데이터가 표시될 위험.

**수정 방향**: `import.meta.env.DEV` 가드 또는 동적 import, 또는 MSW(Mock Service Worker)로 전환

**점수**: 70 × 1.0 = **70**

---

### [R5-002] buyerColumns가 매 렌더마다 재생성 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/tabs/BuyersTab.tsx:~180-250`

**증거**: `buyerColumns` 배열이 컴포넌트 함수 본문에서 직접 생성되며, `useMemo`로 감싸지 않음. 내부에 `onSelect` 콜백 참조.

**문제**: 매 렌더마다 새 배열 객체 + 새 함수 참조 생성 → DataTable에 전달 시 불필요한 리렌더링 유발. Short List 바이어 수가 많을수록 성능 영향 증가.

**수정 방향**: `useMemo(() => [...columns], [onSelect, ...])`로 메모이제이션

**점수**: 70 × 1.0 = **70**

---

### [R5-005] BuyersTab God Component — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/tabs/BuyersTab.tsx`
**교차 검증**: ✅ R6-006과 동일 이슈 — 2개 에이전트 확인

**증거**:
- 515줄
- 9개 상태(useState) + 2개 ref
- 26개 import
- Long List + Short List + Detail Panel + Funnel KPI + Summary Bar 모두 하나의 컴포넌트에 포함

**문제**: 단일 책임 원칙 위반. 하나의 기능 변경(예: Short List 필터 추가)이 전체 컴포넌트에 영향. 테스트, 리팩토링, 코드 리뷰 모두 어려움.

**수정 방향**: 최소한 LongListSection, ShortListSection, BuyerDetailSection으로 분리

**점수**: 70 × 1.0 + 10(교차) = **80**

---

### [R5-006] FunnelKPIBar 상태 Set 하드코딩, BuyerStatus 타입과 동기화 없음 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/components/buyers/FunnelKPIBar.tsx:15-30`
**교차 검증**: ✅ R6-003(Shotgun Surgery)과 관련 이슈 — 2개 에이전트 확인

**증거**:
```tsx
// 3개의 독립 Set이 하드코딩
const NDA_AND_AFTER = new Set([...]);
const CIM_AND_AFTER = new Set([...]);
const DD_STATUSES = new Set([...]);
```

**문제**: `BuyerStatus` enum/type과 동기화되지 않음. 새 상태가 추가되면 이 파일, constants/buyer.ts, 각 뷰 컴포넌트 등 여러 곳을 동시에 수정해야 함(Shotgun Surgery). 타입 안전성 없이 문자열 리터럴 사용.

**수정 방향**: `constants/buyer.ts`에 퍼널 단계별 상태 매핑을 중앙화하고, `BuyerStatus` 타입에서 파생

**점수**: 70 × 1.0 + 10(교차) = **80**

---

### [R6-001] SHORT_LIST_STATUSES에 BID 관련 상태 누락 — [Major/HIGH] — Priority: P1

**파일**: `src/modules/ma/constants/buyer.ts`

**증거**:
```tsx
export const SHORT_LIST_STATUSES: BuyerStatus[] = [
  "NDA_SIGNED", "NDA_REJECTED", "CIM_SENT", "CIM_REVIEWED",
  "DD_GRANTED", "DD_IN_PROGRESS", "DD_COMPLETED",
  "REJECTED",
  // BID_SUBMITTED, BID_NOT_SUBMITTED, BID_DROPPED 누락
];
```

**문제**: Short List 필터링 시 BID 단계 바이어가 제외됨. 입찰 제출 후 바이어가 Short List에서 사라지는 논리적 오류.

**수정 방향**: `BID_SUBMITTED`, `BID_NOT_SUBMITTED`, `BID_DROPPED` 추가

**점수**: 70 × 1.0 = **70**

---

### [R6-005] 핵심 비즈니스 로직에 단위 테스트 없음 — [Major/HIGH] — Priority: P1

**파일**: 테스트 파일 부재

**증거**: `src/modules/ma/` 하위에 `*.test.ts`, `*.test.tsx`, `*.spec.ts` 파일 없음. `buildStageMap`, `FunnelKPIBar` 퍼널 분류, `SHORT_LIST_STATUSES` 필터링 등 핵심 비즈니스 로직이 테스트 미작성.

**문제**: R3-002(REJECTED 중복 카운트), R6-001(BID 상태 누락) 같은 논리 오류가 테스트로 잡히지 않음. 리팩토링 시 회귀 감지 불가.

**수정 방향**: 최소한 `constants/buyer.ts`(상태 분류), `FunnelKPIBar`(퍼널 카운트), `buildStageMap`(단계 매핑)에 대한 단위 테스트 작성

**점수**: 70 × 1.0 = **70**

---

### [R5-003] buildStageMap이 3개 형제 컴포넌트에서 중복 계산 — [Major/MEDIUM] — Priority: P2

**파일**: `src/modules/ma/components/buyers/MarketingGridView.tsx:~24`, `MarketingKanbanView.tsx:~44`, `MarketingTimelineView.tsx:~42`

**증거**: 3개 뷰 모두 `useMemo(() => buildStageMap(overviewData), [overviewData])` 호출. 동일 `overviewData`로 동일 결과 3회 계산.

**문제**: 뷰 전환 시에만 하나가 마운트되므로 실제 성능 영향은 제한적이나, overviewData가 큰 경우 불필요한 계산. 부모에서 한 번 계산하여 전달하는 것이 바람직.

**수정 방향**: `BuyersTab.tsx`에서 `stageMap`을 한 번 계산하여 prop으로 전달

**점수**: 70 × 0.6 = **42**

---

### [R5-004] 100+ 바이어 목록에 가상화 없음 — [Major/MEDIUM] — Priority: P2

**파일**: `src/modules/ma/components/buyers/ShortListMasterList.tsx`

**증거**: 바이어 목록을 `.map()`으로 전체 렌더링. 각 항목에 Badge, StatusDropdown 등 서브 컴포넌트 포함.

**문제**: 현재 바이어 수가 적으면 문제 없으나, 100명 이상이 되면 DOM 노드 수 폭증으로 스크롤 성능 저하. 특히 모바일 환경에서 체감.

**수정 방향**: `@tanstack/react-virtual` 또는 `react-window`로 가상화 (바이어 50명 이상 시)

**점수**: 70 × 0.6 = **42**

---

### [R6-004] devMockBuyers의 상태/is_short_listed 불일치 — [Major/MEDIUM] — Priority: P2

**파일**: `src/modules/ma/constants/devMockBuyers.ts`

**증거**:
```tsx
// mock-4: CONTACTED 상태인데 is_short_listed: true
{ id: "mock-4", status: "CONTACTED", is_short_listed: true, ... }
```

**문제**: CONTACTED는 Long List 단계 상태인데 Short List로 분류됨. 개발 중 Mock 데이터로 테스트 시 잘못된 동작 기대값 형성. R5-001과 결합 시 프로덕션에서도 노출 위험.

**수정 방향**: mock-4의 status를 `"NDA_SIGNED"` 이상으로 변경하거나, `is_short_listed: false`로 수정

**점수**: 70 × 0.6 = **42**

---

### [R6-007] 진행률(pct) 계산 방식이 Timeline과 SummaryBar에서 불일치 — [Major/MEDIUM] — Priority: P2

**파일**: `MarketingTimelineView.tsx` vs `ShortListSummaryBar.tsx`

**증거**:
- Timeline: `pct = (latestStageIndex + 1) / MARKETING_STAGES.length × 100` (위치 기반)
- SummaryBar: 실제 완료된 단계 수 기반

**문제**: 같은 바이어의 진행률이 두 뷰에서 다르게 표시됨. 사용자 혼란 유발.

**수정 방향**: 진행률 계산 로직을 공유 유틸로 통일

**점수**: 70 × 0.6 = **42**

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)

| # | ID | 심각도/신뢰도 | 요약 | 점수 |
|---|-----|-------------|------|------|
| 1 | R3-002 | Major/HIGH 🔁 | REJECTED 3개 Set 중복 → Funnel KPI 왜곡 | 80 |
| 2 | R5-005 | Major/HIGH 🔁 | BuyersTab God Component (515줄, 9 state, 26 import) | 80 |
| 3 | R5-006 | Major/HIGH 🔁 | FunnelKPIBar 상태 Set 하드코딩, 타입 동기화 없음 | 80 |
| 4 | R4-002 | Major/HIGH | mutation onError 8곳에서 BE 에러 상세 무시 | 70 |
| 5 | R4-003 | Major/HIGH | Short List 영역 ErrorBoundary 없음 | 70 |
| 6 | R4-004 | Major/HIGH | 에러 배너 flex 헤더 내부 레이아웃 깨짐 | 70 |
| 7 | R5-001 | Major/HIGH | Dev mock 데이터 프로덕션 번들 포함 | 70 |
| 8 | R5-002 | Major/HIGH | buyerColumns 매 렌더 재생성 (useMemo 없음) | 70 |
| 9 | R6-001 | Major/HIGH | SHORT_LIST_STATUSES에 BID_* 상태 누락 | 70 |
| 10 | R6-005 | Major/HIGH | 핵심 비즈니스 로직 단위 테스트 전무 | 70 |

🔁 = 2개 에이전트 교차 검증됨

### P2 — 개선 권장 (점수: 30-59)

| # | ID | 심각도/신뢰도 | 요약 | 점수 |
|---|-----|-------------|------|------|
| 1 | R5-003 | Major/MEDIUM | buildStageMap 3개 뷰에서 중복 계산 | 42 |
| 2 | R5-004 | Major/MEDIUM | 100+ 바이어 가상화 없음 | 42 |
| 3 | R6-004 | Major/MEDIUM | devMock status/is_short_listed 불일치 | 42 |
| 4 | R6-007 | Major/MEDIUM | Timeline vs SummaryBar 진행률 계산 불일치 | 42 |

---

## Methodology

- **Agents**: R3+R4 통합 에이전트, R5 성능/의존성 에이전트, R6 도메인/테스트/복잡도 에이전트
- **Files scanned**: 12개 (BuyersTab, FunnelKPIBar, MarketingGridView, MarketingKanbanView, MarketingTimelineView, ShortListMasterList, ShortListSummaryBar, BuyerDetailPanel, useMarketingLogs, useTransactions, constants/buyer.ts, devMockBuyers.ts)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 3건 중복 병합 (R3-002=R6-002, R5-005=R6-006, R5-006≈R6-003)

## 검증 투명성

### 검증 통계
- 검증한 가설: 20건
- 거부된 가설 (사전 제거): 3건 (중복)
- 보고된 이슈: 14건
- 거부율: 15%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 중복 | 3 | R6-002 = R3-002, R6-006 = R5-005, R6-003 ≈ R5-006 |

---

## 수정 권장 순서

1. **R6-001 + R3-002** (상태 분류 정합성) — 같은 도메인, 함께 수정
2. **R5-006** (중앙화된 상태 매핑) — R3-002 수정의 기반
3. **R4-002** (onError 통일) — 단순 패턴 적용, 빠른 수정
4. **R5-001 + R6-004** (Mock 데이터 정리) — 번들 최적화 + 데이터 정합성
5. **R5-002** (buyerColumns useMemo) — 단순 래핑
6. **R5-005** (God Component 분리) — 대규모 리팩토링, 별도 스프린트
7. **R4-003 + R4-004** (ErrorBoundary + 에러 배너) — UI 안정성
8. **R6-005** (테스트 작성) — 위 수정 후 테스트 추가
