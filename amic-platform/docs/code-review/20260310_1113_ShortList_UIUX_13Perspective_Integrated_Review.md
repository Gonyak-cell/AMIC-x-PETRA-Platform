# Code Review — Short List UI/UX 개선 통합 리뷰

> **Review Date**: 2026-03-10 10:54 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Short List 탭 UI/UX 개선 — 8개 파일 수정
> **Method**: Quality Gates + 3-Agent Parallel Verified Review + Cross-Verification (중복 병합)
> **Quality Gates**: tsc(PASS) eslint(PASS) build(PASS 33.85s)
> **Review Gates**: Frontend-only (Backend N/A), Agent-Filtering(3개 에이전트 호출)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 3     | HIGH: 3 | P1: 3 |
| Moderate | 9     | HIGH: 5 / MEDIUM: 4 | P2: 6 / P3: 3 |
| Minor    | 7     | HIGH: 4 / MEDIUM: 2 / LOW: 1 | P3: 7 |
| **Total**| **19** | HIGH: **12** / MEDIUM: **6** / LOW: **1** | P1: **3** / P2: **6** / P3: **10** |

**FP Prevention**: 가설 ~28건 검증, 허위 양성 1건 사전 제거 (U-6: Tailwind JIT 동적 클래스 감지 확인) | 교차 검증 3건 수행 (3개 에이전트 독립 발견)

**중복 병합**: 원본 28건 → 중복 8건 제거 + FP 1건 제거 → 최종 19건

---

## Findings

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [M-1] Kanban 카드 ChevronRight 버튼 터치 타겟 44px 미달 — [Major/HIGH] — Priority: P1 (점수: 80)

- **파일**: `MarketingKanbanView.tsx:117`
- **발견 에이전트**: Agent 1 (S3), Agent 2 (A-1), Agent 3 (U-5) — **교차 검증됨**
- **증거**: `p-2`(8px) + 아이콘 16px - `-m-1.5`(6px) = 실제 터치 영역 약 20~32px. WCAG 2.5.5 (44x44px) 미달.
- **영향**: 모바일 사용자가 칸반 카드 상세보기 버튼 터치 어려움
- **대조**: `MarketingGridView.tsx:167`에서는 `min-w-[44px] min-h-[44px]` 보장
- **수정 제안**: `min-w-[44px] min-h-[44px] flex items-center justify-center` 추가

---

#### [M-2] Timeline 상세보기 버튼 터치 타겟 44px 미달 — [Major/HIGH] — Priority: P1 (점수: 80)

- **파일**: `MarketingTimelineView.tsx:140`
- **발견 에이전트**: Agent 1 (S4), Agent 2 (A-2), Agent 3 (U-4) — **교차 검증됨**
- **증거**: `p-1`(4px) + 아이콘 16px = 약 24x24px. WCAG 2.5.5 미달.
- **수정 제안**: `p-2 min-w-[44px] min-h-[44px] flex items-center justify-center`

---

#### [M-3] Kanban 카드 tabIndex={0} 설정 후 키보드 핸들러 없음 — [Major/HIGH] — Priority: P1 (점수: 80)

- **파일**: `MarketingKanbanView.tsx:105-108`
- **발견 에이전트**: Agent 2 (A-3), Agent 3 (U-1) — **교차 검증됨**
- **증거**: `tabIndex={0}`으로 포커스 가능하지만 `onKeyDown` 없음. `role` 속성도 없어 스크린 리더가 요소 목적 파악 불가.
- **영향**: WCAG 2.1.1 위반.
- **수정 제안**: `role="button"` + `onKeyDown` + `aria-label` 추가, 또는 `tabIndex={0}` 제거

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [M-4] ShortListSummaryBar 평균 진행률 분모가 전체 buyers.length 사용 — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **파일**: `ShortListSummaryBar.tsx:38-50`
- **발견 에이전트**: Agent 1 (S1)
- **증거**: `avgPct` 계산 시 `stageMap`에 데이터 없는 바이어는 `continue`로 건너뛰지만, 분모는 `buyers.length` 전체 사용.
- **수정 제안**: 실제 계산에 포함된 바이어 수를 별도 카운터로 사용

---

#### [M-5] border-l-3은 Tailwind 기본 유틸리티에 없는 클래스 — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **파일**: `ShortListMasterList.tsx:137`
- **발견 에이전트**: Agent 3 (U-2)
- **증거**: Tailwind 기본 borderWidth에 `border-l-3` 미존재. 선택 바이어의 좌측 accent 보더 미렌더링.
- **수정 제안**: `border-l-[3px]` (arbitrary value) 또는 `border-l-2`

---

#### [M-6] Grid View 매수자명 셀 onClick 있으나 키보드 접근 불가 — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **파일**: `MarketingGridView.tsx:114-138`
- **발견 에이전트**: Agent 2 (A-6)
- **증거**: `<td>`에 `onClick`만 있고 `tabIndex`, `role`, `onKeyDown` 없음. 행 끝 ChevronRight로 대체 경로 존재.
- **수정 제안**: `tabIndex={0}` + `role="button"` + `onKeyDown` 추가

---

#### [M-17] buildStageMap이 4~5개 컴포넌트에서 중복 호출 — [Moderate/HIGH] — Priority: P2 (점수: 40)

- **파일**: `ShortListSummaryBar.tsx:25`, `ShortListMasterList.tsx:40`, `MarketingGridView.tsx:30`, `MarketingKanbanView.tsx:42`, `MarketingTimelineView.tsx:54`
- **발견 에이전트**: Agent 3b (PERF-01)
- **관점**: 성능
- **증거**: `buildStageMap(buyers)` 함수가 5개 컴포넌트 각각에서 `useMemo`로 계산됨. 동일 Map 3~4회 생성.
- **수정 제안**: `ShortListOverview`에서 한 번만 호출 후 props로 전달.

---

#### [M-18] rounded-lg (8px) vs 디자인 시스템 rounded-dr (12px) 불일치 — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

- **파일**: `ShortListMasterList.tsx:135`
- **발견 에이전트**: Agent 3b (STYLE-02)
- **관점**: 디자인 시스템 정합성
- **증거**: 프로젝트 커스텀 토큰 `rounded-dr` (12px)이 정의되어 있으나 이 컴포넌트만 `rounded-lg` (8px) 사용.
- **수정 제안**: `rounded-lg` → `rounded-dr`

---

#### [M-19] Template literal 조건부 클래스 — cn() 유틸 미사용 — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

- **파일**: `ShortListMasterList.tsx:135-139`
- **발견 에이전트**: Agent 3b (UX-04)
- **관점**: 코드 품질/일관성
- **증거**: 프로젝트에 `cn()` (clsx + tailwind-merge) 유틸이 있으나 이 파일만 template literal 사용.
- **수정 제안**: `cn()` 유틸로 전환

---

### P3 — 저우선 (점수: <30)

---

#### [M-7] ShortListMasterList 목록 컨테이너에 role 누락 — [Moderate/MEDIUM] — Priority: P3 (점수: 24)

- **파일**: `ShortListMasterList.tsx:90-93`
- **수정 제안**: `role="list"` 또는 `role="region"` 추가

---

#### [M-8] ShortListSummaryBar 진행률 바에 role="progressbar" 없음 — [Moderate/MEDIUM] — Priority: P3 (점수: 24)

- **파일**: `ShortListSummaryBar.tsx:121-126`
- **영향**: 제한적 — 부모 aria-label로 값 전달됨

---

#### [M-9] 사이드바 토글 시 레이아웃 시프트 — [Moderate/MEDIUM] — Priority: P3 (점수: 24)

- **파일**: `ShortListOverview.tsx:100-110`
- **영향**: 사이드바 토글 시 메인 콘텐츠 급격 이동 (256px)

---

#### [M-10] summaryMap.get(selectedBuyerId ?? "") 의미 없는 빈 문자열 조회 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **파일**: `ShortListOverview.tsx:172`
- **수정 제안**: `selectedBuyerId ? summaryMap.get(selectedBuyerId) : undefined`

---

#### [M-11] currentIdx=-1 시 nextStage가 MARKETING_STAGES[0]이 됨 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **파일**: `MarketingTimelineView.tsx:109-112`
- **수정 제안**: `currentIdx >= 0` 조건 추가

---

#### [M-12] NOT_TARGET 티어가 TIER_ORDER에서 누락 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **파일**: `ShortListMasterList.tsx` (TIER_ORDER 상수)
- **수정 제안**: `TIER_ORDER`에 `"NOT_TARGET"` 추가

---

#### [M-13] 평균 진행률 카드 filter="all"이라 활성 상태 표시 불가 — [Minor/HIGH] — Priority: P3 (점수: 20)

- **파일**: `ShortListSummaryBar.tsx`
- **영향**: 미미

---

#### [M-14] ShortListViewToggle sm 이하에서 aria-label 없음 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

- **파일**: `ShortListViewToggle.tsx:42`

---

#### [M-15] Grid View Sticky 셀 bg-white가 Drop 행 bg-gray-50과 불일치 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

- **파일**: `MarketingGridView.tsx:115`

---

#### [M-16] "필터 초기화" 버튼 조건부 렌더링 시 미세 레이아웃 시프트 — [Minor/LOW] — Priority: P3 (점수: 6)

- **파일**: `ShortListOverview.tsx:143-151`
- **영향**: 거의 무시 가능

---

## Priority Matrix

### P1 — 스프린트 우선 (3건)
1. **[M-1]** [Major/HIGH 교차검증]: Kanban ChevronRight 터치 타겟 44px 미달 (점수: 80)
2. **[M-2]** [Major/HIGH 교차검증]: Timeline ChevronRight 터치 타겟 44px 미달 (점수: 80)
3. **[M-3]** [Major/HIGH 교차검증]: Kanban 카드 tabIndex 키보드 핸들러 누락 (점수: 80)

### P2 — 개선 권장 (6건)
4. **[M-4]** [Moderate/HIGH]: 평균 진행률 분모 왜곡 (점수: 40)
5. **[M-5]** [Moderate/HIGH]: border-l-3 무효 Tailwind 클래스 (점수: 40)
6. **[M-6]** [Moderate/HIGH]: Grid td onClick 키보드 접근 불가 (점수: 40)
7. **[M-17]** [Moderate/HIGH]: buildStageMap 5개 컴포넌트 중복 호출 (점수: 40)
8. **[M-18]** [Moderate/MEDIUM]: rounded-lg vs rounded-dr 불일치 (점수: 24)
9. **[M-19]** [Moderate/MEDIUM]: cn() 유틸 미사용 (점수: 24)

### P3 — 저우선 (10건)
10. **[M-7]** [Moderate/MEDIUM]: MasterList role 누락 (24)
11. **[M-8]** [Moderate/MEDIUM]: 진행률 바 role="progressbar" 없음 (24)
12. **[M-9]** [Moderate/MEDIUM]: 사이드바 토글 레이아웃 시프트 (24)
13. **[M-10]** [Minor/HIGH]: summaryMap 빈 문자열 조회 (20)
14. **[M-11]** [Minor/HIGH]: nextStage 미진행 바이어 처리 (20)
15. **[M-12]** [Minor/HIGH]: NOT_TARGET 티어 TIER_ORDER 누락 (20)
16. **[M-13]** [Minor/HIGH]: 평균 진행률 filter 활성 상태 (20)
17. **[M-14]** [Minor/MEDIUM]: ViewToggle sm 이하 aria-label (12)
18. **[M-15]** [Minor/MEDIUM]: Sticky 셀 배경색 불일치 (12)
19. **[M-16]** [Minor/LOW]: 필터 초기화 레이아웃 시프트 (6)

---

## Methodology

- **Agents**: 3개 병렬 실행 + 1개 보충 실행
  - Agent 1: 정확성/로직 (Correctness/Logic) — 9건
  - Agent 2: 접근성 (Accessibility/a11y) — 7건
  - Agent 3: UX/성능/스타일 (UX/Performance/Style) — 5건 (1건 FP 제거)
  - Agent 3b (보충): 성능/디자인시스템/코드품질 — 3건 (M-17, M-18, M-19)
- **Files scanned**: 8개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Major 3건 — 2~3개 에이전트 독립 발견 (+10 보너스)

## 검증 투명성

### 검증 통계
- 검증한 가설: ~28건
- 거부된 가설: 1건
- 보고된 이슈: 19건 (중복 병합 후)
- 원본 이슈: 28건
- 중복 제거: 8건
- 허위 양성 제거: 1건

### 교차 검증 결과

| 이슈 | Agent 1 | Agent 2 | Agent 3 | 판정 |
|------|---------|---------|---------|------|
| M-1 (Kanban 터치) | S3 | A-1 | U-5 | CONFIRMED (3/3) |
| M-2 (Timeline 터치) | S4 | A-2 | U-4 | CONFIRMED (3/3) |
| M-3 (Kanban 키보드) | — | A-3 | U-1 | CONFIRMED (2/3) |

---

## 13개 리뷰 관점 커버리지

| # | 관점 | 이슈 수 | 대표 이슈 |
|---|------|--------|----------|
| 1 | 정확성/로직 | 4 | M-4, M-10, M-11, M-13 |
| 2 | 타입 안전성 | 0 | tsc 통과 |
| 3 | WCAG 색상 대비 | 0 | 4.5:1 충족 |
| 4 | 키보드 내비게이션 | 2 | M-3, M-6 |
| 5 | ARIA 정확성 | 3 | M-7, M-8, M-14 |
| 6 | 스크린 리더 | 0 | sr-only 적절 |
| 7 | 터치 타겟 | 2 | M-1, M-2 |
| 8 | prefers-reduced-motion | 0 | 전역 규칙 적용 |
| 9 | UX 일관성 | 2 | M-5, M-19 |
| 10 | 반응형 레이아웃 | 1 | M-9 |
| 11 | CSS/Tailwind | 2 | M-5, M-15 |
| 12 | 성능 | 1 | M-17 |
| 13 | 디자인 시스템 정합성 | 2 | M-12, M-18 |
