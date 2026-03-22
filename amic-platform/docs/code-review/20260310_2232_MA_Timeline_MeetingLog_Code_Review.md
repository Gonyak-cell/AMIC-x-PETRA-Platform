# Code Review — MA Timeline MeetingLog Integration

> **Review Date**: 2026-03-10 22:32
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: Short List MarketingTimelineView 미팅 로그 인라인 삽입 기능 (신규 3파일 + 수정 1파일)
> **Method**: Quality Gates + Verified Single-Agent Review
> **Quality Gates**: tsc(PASS) eslint(PASS) build(PASS)
> **Review Gates**: FE-only 변경 — 백엔드 에이전트 제외

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 0     | — | — |
| Moderate | 4     | HIGH: 4 | P2: 4 |
| Minor    | 4     | HIGH: 2 / MEDIUM: 1 / LOW: 1 | P3: 4 |
| **Total**| **8** | HIGH: **6** / MEDIUM: **1** / LOW: **1** | P2: **4** / P3: **4** |

## 잘 된 점

1. **`timelineItems.ts` 유틸 분리** — 렌더링 로직과 데이터 병합을 깔끔하게 분리. Discriminated union 타입으로 타입 안전성 우수.
2. **N+1 방지** — 트랜잭션 전체 MARKETING 미팅을 1회 fetch → `meetingsByBuyer` Map으로 O(1) 조회.
3. **기존 패턴 준수** — `CHANNEL_ICON`, `STATUS_VARIANT` 패턴, `InlineLogInput`의 UX 패턴 차용.
4. **접근성** — 모든 폼 필드에 `aria-label`, `sr-only` 설명 포함.
5. **메모이제이션** — `meetingsByBuyer`, `sorted` 모두 `useMemo` 적용.

## Findings

### P2 — 개선 권장

#### [R2] CHANNEL_ICON / STATUS_VARIANT / STATUS_LABEL 중복 선언 — [Moderate/HIGH] — P2 (40점)

**파일**: `TimelineMeetingCard.tsx:13-36` + `BuyerMeetingTimeline.tsx:21-44`
**설명**: 두 파일에서 동일한 3개 매핑 객체가 중복 선언됨. `STATUS_VARIANT`와 `STATUS_LABEL`은 값까지 동일. `CHANNEL_ICON`은 아이콘 크기만 차이(h-4 vs h-3.5). 새 MeetingStatus/Channel 추가 시 동기화 누락 위험.
**수정 제안**: `STATUS_VARIANT`, `STATUS_LABEL`은 `constants/meeting.ts`로 추출. `CHANNEL_ICON`은 크기 파라미터 팩토리 함수로 통합.

#### [R4] InlineMeetingForm에서 에러 상태 UI 미표시 — [Moderate/HIGH] — P2 (40점)

**파일**: `InlineMeetingForm.tsx:41-54`
**설명**: `createLog.isError` 상태에 대한 UI 피드백 없음. 기존 `InlineLogInput`도 동일 패턴이므로 프로젝트 컨벤션에는 부합.
**수정 제안**: 프로젝트 일관성 관점 현행 유지 가능. 개선 시 `createLog.isError`일 때 폼 테두리 색상 변경(border-red-300).

#### [R6] IIFE 패턴의 렌더링 복잡성 — [Moderate/HIGH] — P2 (40점)

**파일**: `MarketingTimelineView.tsx:184-251`
**설명**: JSX 내부 70행 분량 IIFE로 `prevStageDate` 클로저 유지. 경과일수 계산에 필요하지만 가독성 저해.
**수정 제안**: `timelineItems`를 `useMemo`에서 `{ ...item, elapsed }` 형태로 사전 계산하면 IIFE 제거 가능. 또는 `TimelineStageItem`/`TimelineMeetingItem` 컴포넌트 별도 분리.

#### [R8] buildTimelineItems 호출에 useMemo 누락 — [Moderate/HIGH] — P2 (40점)

**파일**: `MarketingTimelineView.tsx:136-138`
**설명**: `sorted.map()` 내부에서 매 렌더링마다 `buildTimelineItems` 호출(O(n log n)). 현실적 Short List 규모(10~30명)에서는 영향 미미.
**수정 제안**: 현재 규모 허용 가능. 스케일 시 `buyerId → TimelineItem[]` Map을 `useMemo`로 사전 계산.

### P3 — 저우선

#### [R1] 미사용 export getItemDate — [Minor/HIGH] — P3 (20점)

**파일**: `timelineItems.ts:43`
**설명**: `getItemDate` 함수가 export되어 있으나 프로젝트 어디서도 사용하지 않음.
**수정 제안**: 삭제하거나 export 제거.

#### [R3] buildTimelineItems 빈 문자열 방어 부재 — [Minor/MEDIUM] — P3 (12점)

**파일**: `timelineItems.ts:28-31`
**설명**: `meeting_date`가 `string`(non-nullable)이고 호출처에서 truthy 체크로 빈 문자열도 걸러지므로 실질 리스크 낮음.
**수정 제안**: JSDoc으로 "YYYY-MM-DD 형식, 빈 문자열 금지" 명시.

#### [R5] meetingsByBuyer useMemo 의존성 범위 — [Minor/HIGH] — P3 (20점)

**파일**: `MarketingTimelineView.tsx:53-66`
**설명**: 의존성 `[meetingData]` → `[meetingData?.items]`로 좁히면 의도 명확.
**수정 제안**: `[meetingData?.items]`로 변경 (기능 무영향).

#### [R7] buyer_id optional이지만 필수 전달 — [Minor/LOW] — P3 (6점)

**파일**: `InlineMeetingForm.tsx:44-52`
**설명**: 타입상 optional이나 마케팅 맥락에서 항상 필수 전달. 올바른 설계. 확인 사항.

## Methodology

- Agents: code-reviewer (1개)
- Excluded Agents: api-auditor, security-auditor, a11y-auditor (FE-only 스코프, 백엔드 없음)
- Files scanned: 4
- Protocol: Verified Claim Protocol v1.1
- Cross-verification: 생략 (Critical/Major 0건)

## 검증 투명성

### 검증 통계
- 검증한 가설: 10건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 8건
- 거부율: 20%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | `rounded-dr` 오타 의심 → 프로젝트 전체에서 디자인 토큰으로 확인 |
| 신뢰도 불충분 | 1 | meeting_date nullable 의심 → 타입 확인 결과 non-nullable |
