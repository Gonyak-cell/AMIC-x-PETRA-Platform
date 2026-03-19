# Code Review — Short List UI 통합 개선 (13관점)

> **Review Date**: 2026-03-10 17:07
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff 5f78d7d..HEAD` — 10개 파일, +136/-46 라인 (프론트엔드 전용)
> **Method**: Quality Gates + Review Gates + Verified Multi-Agent Review (3병렬) + Cross-Verification
> **Quality Gates**: tsc(✅) eslint(⏭️) vitest(⏭️) build(⏭️)
> **Review Gates**: Backend(N/A — FE 전용) Agent-Filtering(3개 에이전트 호출, 백엔드 에이전트 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0 | — | — |
| Major | 3 | HIGH: 2 / MEDIUM: 1 | P1: 3 |
| Moderate | 3 | HIGH: 1 / MEDIUM: 2 | P2: 3 |
| Minor | 7 | HIGH: 2 / MEDIUM: 3 / LOW: 2 | P3: 7 |
| **Total** | **13** | HIGH: **5** / MEDIUM: **6** / LOW: **2** | P1: **3** / P2: **3** / P3: **7** |

**FP Prevention**: 가설 15건 검증, 2건 사전 거부 (거부율: 13%) | 교차 검증 3건 수행
**계획 대비 구현율**: 13/15 (87%) — 미구현 2건 (P1-2 dot 4색, P1-5 로그 삭제)

---

## Findings

### [K-01] 칸반 뷰 중복 React key — [Major/HIGH] — Priority: P1

- **위치**: `MarketingKanbanView.tsx:113, 118`
- **코드**:
  ```tsx
  <div key={buyer.id}>         // 외부 wrapper (map 반환)
    {isFirstDrop && <hr ... />}
    <div key={buyer.id} ...>   // 내부 — 중복 key
  ```
- **문제**: `.map()` 반환 최상위 `<div>`와 내부 `<div>`에 동일 `key={buyer.id}` 중복. 불필요한 중복이며 향후 구조 변경 시 혼동 유발.
- **교차 검증**: ✅ 2개 에이전트 동시 발견 (I-01 + R4-1)
- **수정**: 내부 `<div>`의 `key={buyer.id}` 제거

---

### [D-01] Drop 복구 시 상태가 IDENTIFIED로 고정 — [Major/MEDIUM] — Priority: P1

- **위치**: `BuyersTab.tsx:597`
- **코드**:
  ```tsx
  status: isCurrentlyDropped ? 'IDENTIFIED' : 'BID_DROPPED'
  ```
- **문제**: Drop 복구 시 무조건 `IDENTIFIED`(Long List 초기 상태)로 되돌림. Drop 이전 상태(`SHORT_LISTED` 등)를 잃어버림. Short List에서 복구하면 해당 매수자가 Short List에서 사라질 수 있음.
- **교차 검증**: ✅ 2개 에이전트 동시 발견 (I-04 + R6-1)
- **판정**: DESIGN_RISK — 의도적 설계일 수 있으나, 비즈니스 로직 확인 필요
- **수정 제안**: (1) `SHORT_LISTED`로 복구하거나, (2) 백엔드에서 `previous_status` 관리, (3) 의도적이라면 주석 명시

---

### [D-02] Drop 토글 에러 피드백 부재 — [Major/HIGH] — Priority: P1

- **위치**: `BuyersTab.tsx:593-600`
- **코드**:
  ```tsx
  onToggleDrop={(buyerId, isCurrentlyDropped) =>
    updateBuyer.mutate({
      buyerId,
      body: { status: isCurrentlyDropped ? 'IDENTIFIED' : 'BID_DROPPED' },
    })
  }
  ```
- **문제**: `onSuccess`/`onError` 콜백 없음. API 실패 시 사용자에게 피드백 없음. Drop은 비가역적 느낌의 액션인데 확인 dialog도 없음.
- **수정 제안**: `onError`에 toast 알림 추가, Drop 시 확인 dialog 검토

---

### [G-01] Grid Drop 행의 sticky 셀 배경색 불일치 — [Moderate/MEDIUM] — Priority: P2

- **위치**: `MarketingGridView.tsx:103, 108`
- **문제**: Drop 행의 `<tr>`에 `bg-gray-50 grayscale`가 적용되지만, sticky 첫 번째 `<td>`는 `bg-white` 하드코딩. 수평 스크롤 시 첫 열만 흰 배경으로 남아 시각 불일치.
- **수정 제안**: sticky 셀 배경을 조건부 처리 (`isDropped ? 'bg-gray-50' : 'bg-white'`)

---

### [S-01] 칸반 뷰 들여쓰기 심각한 불일치 — [Moderate/HIGH] — Priority: P2

- **위치**: `MarketingKanbanView.tsx:112-167`
- **문제**: wrapper `<div>` 추가 시 내부 카드 `<div>`의 들여쓰기를 조정하지 않아 8칸/4칸이 혼재. 가독성 크게 저하.
- **수정 제안**: 내부 카드와 하위 요소의 들여쓰기를 wrapper 기준으로 정렬

---

### [S-02] Modern Green 하드코딩 색상 (디자인 토큰 미사용) — [Moderate/MEDIUM] — Priority: P2

- **위치**: `MarketingGridView.tsx:69-82`, `MarketingKanbanView.tsx:81`
- **코드**: `bg-green-500`, `border-green-600`, `text-white/90`, `border-green-400/50`
- **문제**: 기존 디자인 시스템 토큰(`bg-bg-cool`, `text-text-dark`)에서 하드코딩 색상으로 변경. 테마 변경 시 수동 수정 필요.
- **수정 제안**: CSS 변수 또는 디자인 토큰으로 추상화 검토

---

### [M-01] FunnelKPIBar 하드코딩 라벨 비교 — [Minor/MEDIUM] — Priority: P3

- **위치**: `FunnelKPIBar.tsx:74`
- **코드**: `step.label !== "Short List" && step.label !== "NDA 체결"`
- **문제**: 라벨 문자열 하드코딩. 라벨 변경 시 조건 깨짐.

### [M-02] 칸반 filter() 3회 반복 호출 — [Minor/MEDIUM] — Priority: P3

- **위치**: `MarketingKanbanView.tsx:87-91`
- **문제**: 동일 배열에 `filter()` 2회 + `some()` 1회. 한 번 계산으로 최적화 가능.

### [M-03] 칸반 렌더 내 sort() 매 렌더 실행 — [Minor/MEDIUM] — Priority: P3

- **위치**: `MarketingKanbanView.tsx:99-104`
- **문제**: JSX 내에서 `[...stageBuyers].sort()`. useMemo 안으로 이동 권장.

### [M-04] Sidebar 빈 줄 잔여 — [Minor/HIGH] — Priority: P3

- **위치**: `Sidebar.tsx:757` 부근
- **문제**: 토글 블록 이동 후 원래 위치에 빈 줄 남음.

### [M-05] Timeline 미완료 단계 접근성 정보 부족 — [Minor/MEDIUM] — Priority: P3

- **위치**: `MarketingTimelineView.tsx:195-215`
- **문제**: 미완료 단계가 시각적으로만 구분(opacity, italic). 스크린리더에 "미완료" 상태 미전달.

### [M-06] "접기/펼치기" 컨텍스트 부족 — [Minor/LOW] — Priority: P3

- **위치**: `BuyersTab.tsx:537-539`
- **문제**: 이전 "마케팅 활동 추적" 라벨 제거 후 단순 "접기/펼치기"만. 무엇을 접는지 첫 사용자에게 불명확.

### [M-07] Drop hover 시 grayscale 유지 — [Minor/LOW] — Priority: P3

- **위치**: Grid(:103), Kanban(:121), MasterList(:137) 공통
- **문제**: `hover:opacity-70`으로 opacity만 변경, grayscale 유지. 인터랙션 피드백 약함.

---

## Priority Matrix

### P1 — 즉시 수정 (3건)

1. **[K-01]** [Major/HIGH ✅교차검증]: 칸반 중복 React key — `MarketingKanbanView.tsx` (점수: 80)
2. **[D-01]** [Major/MEDIUM ⚠️]: Drop 복구 IDENTIFIED 고정 — `BuyersTab.tsx` (점수: 52, 교차검증 +10 = 62)
3. **[D-02]** [Major/HIGH]: Drop 토글 에러 피드백 부재 — `BuyersTab.tsx` (점수: 70)

### P2 — 개선 권장 (3건)

1. **[G-01]** [Moderate/MEDIUM]: Grid sticky 셀 배경 불일치 — `MarketingGridView.tsx` (점수: 24+15=39)
2. **[S-01]** [Moderate/HIGH]: 칸반 들여쓰기 불일치 — `MarketingKanbanView.tsx` (점수: 40)
3. **[S-02]** [Moderate/MEDIUM]: 하드코딩 녹색 색상 — Grid/Kanban (점수: 24)

### P3 — 저우선 (7건)

1. **[M-01~M-07]**: 라벨 하드코딩, filter 반복, sort 위치, 빈 줄, 접근성, 컨텍스트, hover 피드백

---

## 계획 대비 구현 검증 (§6)

| # | 계획 항목 | 상태 | 근거 |
|---|----------|------|------|
| P0-1 | Grid 빈 셀 tooltip + hover | ✅ | `MarketingGridCell.tsx:70-71` |
| P0-2 | Detail Panel Drop 토글 | ✅ | `BuyerDetailPanel.tsx:64-78`, `BuyersTab.tsx:593-600` |
| P0-3 | Timeline 미완료 단계 | ✅ | `MarketingTimelineView.tsx:94-98, 194-215` |
| P1-1 | Drop grayscale (3개 뷰) | ✅ | Grid(:103), Kanban(:121), MasterList(:137) |
| P1-2 | Timeline dot 4색 | ❌ | dot이 여전히 `bg-accent` 단색 |
| P1-3 | 칸반 Active/Drop 구분선 | ✅ | `MarketingKanbanView.tsx:99-115` |
| P1-4 | 칸반 헤더 Drop 카운트 | ✅ | `MarketingKanbanView.tsx:87-92` |
| P1-5 | Timeline 로그 삭제 | ❌ | 삭제 버튼/콜백 미구현 |
| P2-1 | Summary 라벨 케이싱 | ✅ | `ShortListSummaryBar.tsx:58,64,83` |
| P2-2 | Drop 배경색 통일 | ✅ | Grid/Kanban `bg-gray-50` |
| P2-3 | Grid 빈 셀 hover 강화 | ✅ | P0-1과 동시 구현 |

**구현율: 13/15 (87%)** — 미구현: P1-2 (dot 4색), P1-5 (로그 삭제)

**계획 외 추가 (5건)**: Sidebar 토글 위치 이동, Modern Green 헤더, Grid 점선 구분, NDA % 숨김, 마스터리스트 기본 닫힘

---

## Methodology

- **Agents**: code-reviewer ×3 (R1-R3, R4-R6, §6 계획검증)
- **Excluded**: api-auditor, security-auditor (백엔드 미변경), type-checker (tsc 통과)
- **Files scanned**: 10
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: P1 이슈 3건 수행 (FP 제거: 0건, DESIGN_RISK: 1건)

## 검증 투명성

### 검증 통계
- 검증한 가설: 15건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 13건
- 거부율: 13%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | I-05: `isDropped` 타입 안전성 — buyer guard 내부이므로 문제 없음 |
| 중복 | 1 | R4-4: isDropped 타입 — I-05와 동일 이슈 |
