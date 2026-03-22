# Code Review — Short List 탭 보충 심층 리뷰 (R2–R6)

> **Review Date**: 2026-03-09 13:45
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Short List 탭 관련 13개 파일 — 이전 리뷰(R1 + R6 일부) 미수행 관점 보충
> **Method**: Review Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: SKIPPED (이전 세션에서 tsc ✓, eslint ✓ 확인 완료)
> **Review Gates**: Backend(unavailable) Agent-Filtering(3개 에이전트 호출)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 12    | HIGH: 4 / MEDIUM: 8 / LOW: 0 | P1: 4 / P2: 8 |
| Moderate | 0     | — | — |
| Minor    | 0     | — | — |
| **Total**| **12** | HIGH: **4** / MEDIUM: **8** / LOW: **0** | P1: **4** / P2: **8** |

**FP Prevention**: 가설 14건 검증, 2건 사전 거부 (거부율: 14%) | 교차 검증 7건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 8건 하향 조정 (Major/MEDIUM → P2)

---

## Findings

### P1 — 스프린트 우선 (점수: 60–89)

---

#### [R3-DATA-01] Marketing Log CRUD 시 overview 캐시 미갱신 → stale 데이터 — [Major/HIGH] — Priority: P1

**점수**: 70

**위치**: `src/modules/ma/hooks/useMarketingLogs.ts:51-126`

**문제**: `useCreateMarketingLog`, `useUpdateMarketingLog`, `useDeleteMarketingLog` 3개 mutation의 `onSuccess`에서 buyer-specific 쿼리키만 invalidate하고, overview 쿼리키 `["ma", "transactions", txnId, "short-list", "overview"]`를 invalidate하지 않음.

**영향**: 마케팅 로그 CRUD 후 FunnelKPIBar와 마케팅 단계 트래커가 이전 데이터를 표시. 사용자가 페이지를 새로고침해야만 최신 데이터 반영.

**수정 방향**:
```typescript
// onSuccess에 추가
queryClient.invalidateQueries({
  queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
});
```

**검증**: Read로 `useMarketingLogs.ts` 직접 확인. 3개 mutation 모두 동일 패턴.

---

#### [R5-PERF-02] 3개 뷰 컴포넌트에서 buildStageMap + sort 매 렌더 재생성 — [Major/HIGH] — Priority: P1

**점수**: 70

**위치**:
- `src/modules/ma/components/buyers/MarketingGridView.tsx:33`
- `src/modules/ma/components/buyers/MarketingKanbanView.tsx:44`
- `src/modules/ma/components/buyers/MarketingTimelineView.tsx:42`

**문제**: `buildStageMap(overviewData)`와 `[...buyers].sort(...)` 호출이 `useMemo` 없이 매 렌더마다 실행. `overviewData`가 수십~수백 건이면 Map 생성 + 정렬이 불필요하게 반복.

**수정 방향**:
```typescript
const stageMap = useMemo(() => buildStageMap(overviewData), [overviewData]);
const sorted = useMemo(() => [...buyers].sort(...), [buyers]);
```

**검증**: Read로 3개 파일 직접 확인. 모두 동일 패턴.

---

#### [SL-006] Short List 12+ 컴포넌트에 테스트 0건 — [Major/HIGH] — Priority: P1

**점수**: 85 (70 + 15 교차 검증 보너스)

**위치**: `src/modules/ma/components/buyers/` 전체 디렉토리

**문제**: FunnelKPIBar, MarketingGridView, MarketingKanbanView, MarketingTimelineView, MarketingStageTracker, ShortListMasterList, ShortListSummaryBar, BuyerDetailPanel 등 비즈니스 크리티컬 컴포넌트에 단위 테스트가 전무.

**영향**: 퍼널 KPI 집계 로직, 단계 분류 로직, 정렬/필터 로직 등의 정확성을 자동 검증할 수 없음. 리그레션 리스크 높음.

**수정 방향**: 최소한 FunnelKPIBar (집계 로직), buildStageMap (유틸), BuyerStatus 매핑 로직에 대한 단위 테스트 작성 권장.

**검증**: Glob `src/modules/ma/**/*.test.*` — 0건 확인. 교차 검증으로 재확인.

---

#### [R3-API-04] BE dict[str, str|None] vs FE Record<MarketingStage, ...> 타입 불일치 — [Major/HIGH] — Priority: P1

**점수**: 70

**위치**:
- BE: `deal-mgmt/app/schemas/marketing_log.py:44` — `stages: dict[str, str | None]`
- FE: `src/modules/ma/types/marketing_log.ts:33-36` — `stages: Record<MarketingStage, string | null>`

**문제**: 백엔드는 임의 문자열 키를 허용하는 `dict[str, str | None]`이고, 프론트엔드는 특정 `MarketingStage` 리터럴 타입만 허용하는 `Record<MarketingStage, ...>`. BE에서 오타나 새 단계명을 보내면 FE에서 타입 불일치 발생.

**영향**: 런타임에서는 동작하지만, 타입 안전성 보장 불가. 새 단계 추가 시 양쪽 동기화 누락 리스크.

**수정 방향**: BE에서 `Literal` 또는 `Enum`으로 키를 제한하거나, FE에서 `Partial<Record<...>>`로 유연하게 처리.

**검증**: Read로 양쪽 파일 직접 확인.

---

### P2 — 개선 권장 (점수: 30–59)

---

#### [SL-001/R3-DATA-02/SL-007] FunnelKPIBar 상태 Set + BUYER_STATUS_OPTIONS 누락 값 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 52 (42 + 10 교차 검증 보너스)

⚠️ MEDIUM 신뢰도로 인해 P1 → P2 하향 조정

**위치**:
- `src/modules/ma/components/buyers/FunnelKPIBar.tsx:7-40`
- `src/modules/ma/constants/buyer.ts:96-110`

**문제**:
1. FunnelKPIBar의 `NDA_AND_AFTER`, `CIM_AND_AFTER`, `DD_STATUSES` Set에 REJECTED, BID_NOT_SUBMITTED, BID_DROPPED 상태 누락 → 해당 상태의 바이어가 퍼널 카운트에서 제외
2. `BUYER_STATUS_OPTIONS`에 4개 상태 누락 (REJECTED, BID_SUBMITTED, BID_NOT_SUBMITTED, BID_DROPPED) → 드롭다운에서 선택 불가

**영향**: 퍼널 KPI 수치 부정확, 일부 상태 선택 불가. 단, 현재 프로덕션에서 해당 상태를 사용하지 않을 수 있어 MEDIUM 신뢰도.

**검증**: Read로 FunnelKPIBar.tsx와 buyer.ts 직접 확인. BuyerStatus 타입에는 17개 값 존재하나 Set/Options에는 일부 누락.

---

#### [SL-003] 에러 배너 위치 및 refetchBuyers 호출 부정확 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/tabs/BuyersTab.tsx:293-308`

**문제**: overview 에러 시에도 `refetchBuyers()`를 호출하여 의미 없는 재요청. overview 전용 `refetchOverview()`를 호출해야 함.

**검증**: Read로 BuyersTab.tsx 확인. 에러 배너의 재시도 버튼이 `refetchBuyers` 하나로 통합되어 있음.

---

#### [R5-PERF-01] overviewMerged 스프레드 매 렌더 재생성 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/tabs/BuyersTab.tsx:227`

**문제**: `[...(shortListOverview ?? []), ...devOverview]` 스프레드가 매 렌더마다 새 배열 생성. `useMemo` 없이 하위 컴포넌트에 전달되어 불필요한 리렌더 유발.

**수정 방향**: `useMemo`로 감싸되, dev mock 부분은 `import.meta.env.DEV` 조건부이므로 프로덕션에서는 단순 `shortListOverview ?? []` 처리.

---

#### [R5-PERF-03] ShortListMasterList O(N×M) find 패턴 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/components/buyers/ShortListMasterList.tsx`

**문제**: 바이어 목록 렌더 시 각 바이어마다 `overviewData.find(o => o.buyer_id === buyer.id)` 호출. N명 바이어 × M건 overview = O(N×M) 탐색.

**수정 방향**: `buildStageMap()`처럼 Map으로 사전 변환 후 O(1) 조회.

---

#### [R5-PERF-04] FunnelKPIBar 5회 배열 순회 useMemo 미적용 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/components/buyers/FunnelKPIBar.tsx:43-64`

**문제**: `steps` 배열 계산 시 4개 `.filter()` + 전환율 계산이 `useMemo` 없이 매 렌더 실행.

**수정 방향**: `useMemo(() => [...steps 계산], [buyers])`.

---

#### [R5-DEP-01] BuyersTab 8개 상태 변수 → 리렌더 증폭 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/tabs/BuyersTab.tsx` (상단 state 선언부)

**문제**: `selectedBuyerId`, `selectedTab`, `viewMode`, `searchQuery`, `statusFilter`, `sortOrder`, `filterSource`, `page` 8개 독립 `useState` → 어느 하나 변경 시 전체 컴포넌트 리렌더.

**수정 방향**: 관련 상태를 `useReducer`로 그룹화하거나, 하위 컴포넌트에 상태를 위임하여 리렌더 범위 축소.

---

#### [SL-004] ShortListSummaryBar 혼합 데이터 소스 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/components/buyers/ShortListSummaryBar.tsx`

**문제**: 일부 집계는 `buyers` 배열에서, 일부는 `overviewData`에서 가져와 데이터 소스 불일치 가능성.

---

#### [SL-005] MarketingTimelineView currentIdx=-1 엣지 케이스 — [Major/MEDIUM ⚠️] — Priority: P2

**점수**: 42

**위치**: `src/modules/ma/components/buyers/MarketingTimelineView.tsx`

**문제**: `MARKETING_STAGES.indexOf(currentStage)` 결과가 -1일 때 (매핑 안 되는 상태) 타임라인 UI가 깨질 수 있음.

**수정 방향**: `-1`일 때 기본값 0 또는 "상태 미정" 표시.

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60–89)
1. [SL-006] [Major/HIGH]: Short List 12+ 컴포넌트 테스트 0건 — buyers/ (점수: 85)
2. [R3-DATA-01] [Major/HIGH]: Marketing Log CRUD overview 캐시 미갱신 — useMarketingLogs.ts (점수: 70)
3. [R5-PERF-02] [Major/HIGH]: 3개 뷰 buildStageMap+sort useMemo 미적용 — Grid/Kanban/Timeline (점수: 70)
4. [R3-API-04] [Major/HIGH]: BE dict vs FE Record 타입 불일치 — marketing_log schema (점수: 70)

### P2 — 개선 권장 (점수: 30–59)
1. [SL-001] [Major/MEDIUM ⚠️]: FunnelKPIBar 상태 Set + STATUS_OPTIONS 누락 — FunnelKPIBar+buyer.ts (점수: 52)
2. [SL-003] [Major/MEDIUM ⚠️]: 에러 배너 refetchBuyers 호출 부정확 — BuyersTab.tsx (점수: 42)
3. [R5-PERF-01] [Major/MEDIUM ⚠️]: overviewMerged 스프레드 매 렌더 재생성 — BuyersTab.tsx (점수: 42)
4. [R5-PERF-03] [Major/MEDIUM ⚠️]: ShortListMasterList O(N×M) find — ShortListMasterList.tsx (점수: 42)
5. [R5-PERF-04] [Major/MEDIUM ⚠️]: FunnelKPIBar 5회 배열 순회 useMemo 미적용 — FunnelKPIBar.tsx (점수: 42)
6. [R5-DEP-01] [Major/MEDIUM ⚠️]: BuyersTab 8개 상태 변수 리렌더 증폭 — BuyersTab.tsx (점수: 42)
7. [SL-004] [Major/MEDIUM ⚠️]: ShortListSummaryBar 혼합 데이터 소스 — ShortListSummaryBar.tsx (점수: 42)
8. [SL-005] [Major/MEDIUM ⚠️]: MarketingTimelineView currentIdx=-1 엣지 케이스 — MarketingTimelineView.tsx (점수: 42)

---

## Methodology

- **Agents**: Round 2–4 Agent (Security/Data/Error), Round 5 Agent (Perf/Deploy/Deps), Round 6 Agent (Domain/Test/Complexity)
- **Excluded Agents**: Backend security/API auditor (백엔드 unavailable)
- **Files scanned**: 13개 (Short List 탭 관련)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major HIGH 이슈 7건 수행
- **Backend availability**: FDD(unavailable) KIIS(unavailable) IM(unavailable) MA(partial — schemas only)

## 검증 투명성

### 검증 통계
- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 12건
- 거부율: 14%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 2 | R3-DATA-03/SL-002: "프로덕션 dev mock 노출" → `import.meta.env.DEV` 가드 존재 확인 |
| 설계 리스크 | 1 | R3-DATA-05: dev mock buyer detail — dev 전용 코드로 DESIGN_RISK 분류 (보고에서 제외) |

---

## 리뷰 관점 커버리지

| # | 관점 | 라운드 | 상태 |
|---|------|--------|------|
| 1 | 코드 정합성 (§1) | R1 | ✅ 이전 리뷰 완료 |
| 2 | 완전성 (§2) | R1 | ✅ 이전 리뷰 완료 |
| 3 | 코드 품질 (§3) | R1 | ✅ 이전 리뷰 완료 |
| 4 | 안정성 (§4) | R1 | ✅ 이전 리뷰 완료 |
| 5 | 보안 (§5) | R2 | ✅ 이번 리뷰 수행 (프론트엔드 범위, 이슈 없음) |
| 6 | 데이터 무결성 | R3 | ✅ 이번 리뷰 수행 → R3-DATA-01, R3-API-04 |
| 7 | API 계약 | R3 | ✅ 이번 리뷰 수행 → R3-API-04 |
| 8 | 에러 처리 | R4 | ✅ 이번 리뷰 수행 → SL-003 |
| 9 | 관찰 가능성 | R4 | ✅ 이번 리뷰 수행 (프론트엔드 범위, 이슈 없음) |
| 10 | 성능 | R5 | ✅ 이번 리뷰 수행 → R5-PERF-01~04, R5-DEP-01 |
| 11 | 도메인 로직 | R6 | ✅ 이번 리뷰 수행 → SL-001, SL-004, SL-005 |
| 12 | 테스트 품질 | R6 | ✅ 이번 리뷰 수행 → SL-006 |
| 13 | 인지 복잡도 | R6 | ✅ 이번 리뷰 수행 → R5-DEP-01 (BuyersTab 상태 복잡도) |

**13/13 관점 커버리지 달성.**
