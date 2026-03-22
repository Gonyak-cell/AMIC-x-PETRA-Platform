# Code Review — MA Timeline MeetingLog (Post-Fix)

> **Review Date**: 2026-03-10 22:49
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 6 files — timelineItems.ts, meeting.ts, TimelineMeetingCard.tsx, BuyerMeetingTimeline.tsx, InlineMeetingForm.tsx, MarketingTimelineView.tsx
> **Method**: Quality Gates + Verified Single-Agent Review
> **Quality Gates**: tsc(PASS) build(PASS)
> **Review Gates**: Backend(not applicable — FE only) Agent-Filtering(1개 에이전트 호출, 0개 제외)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 0     | — | — |
| Moderate | 3     | HIGH: 3 | P2: 3 |
| Minor    | 3     | HIGH: 1 / MEDIUM: 2 | P3: 3 |
| **Total**| **6** | HIGH: **4** / MEDIUM: **2** | P2: **3** / P3: **3** |

**FP Prevention**: 가설 13건 검증, 7건 사전 거부 (거부율: 54%)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 2건 (Minor → P3 유지)
- LOW 신뢰도 이슈 0건

## Findings

---

### [MTL-04] handleSubmit에 isPending 가드 누락 — Enter 키 중복 제출 가능 — [Moderate/HIGH] — Priority: P2

**파일**: `InlineMeetingForm.tsx:43-56`
**카테고리**: 방어적 프로그래밍

**문제**: `handleSubmit` 함수에서 `createLog.isPending` 상태를 확인하지 않음. 버튼은 `disabled={createLog.isPending}`으로 보호되지만, `<form onSubmit={handleSubmit}>`에서 Enter 키로 제출 시 isPending 가드를 우회하여 중복 뮤테이션 발생 가능.

**현재 코드**:
```tsx
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  if (!title.trim() || !date) return;
  // isPending 체크 없음 — Enter 키로 중복 제출 가능
  createLog.mutate({ ... });
};
```

**권장 수정**:
```tsx
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  if (!title.trim() || !date || createLog.isPending) return;
  createLog.mutate({ ... });
};
```

**검증**: Read로 InlineMeetingForm.tsx 확인. 버튼 disabled 속성은 존재하나 handleSubmit 함수 내부에 isPending 가드 없음 확인.

**Self-Challenge**: SC-1(✓ 코드 확인) SC-2(✓ 실제 중복 제출 가능) SC-3(✓ 수정 명확) SC-4(✓ 기존 동작 유지) SC-5(✓ Enter 키 시나리오 재현 가능)

---

### [MTL-01] CHANNEL_ICON 맵 두 파일에 중복 정의 — [Moderate/HIGH] — Priority: P2

**파일**: `TimelineMeetingCard.tsx:8-14`, `BuyerMeetingTimeline.tsx:21-27`
**카테고리**: DRY 원칙

**문제**: 동일한 `CHANNEL_ICON` 맵이 두 컴포넌트에 별도 정의됨. 아이콘 크기만 다름 (`h-3.5 w-3.5` vs `h-4 w-4`). 새 채널 타입 추가 시 두 곳 동시 수정 필요 — 동기화 누락 위험.

**현재 상태**:
- `TimelineMeetingCard.tsx`: `VIDEO: <Video className="h-3.5 w-3.5" />`
- `BuyerMeetingTimeline.tsx`: `VIDEO: <Video className="h-4 w-4" />`

**권장 방향**: 아이콘 매핑 로직을 함수로 추출하여 `constants/meeting.ts`에 이동하고 size를 파라미터로 받거나, 또는 현재 수준에서는 주석으로 상호 참조 추가.

**검증**: Read로 양쪽 파일 확인. 5개 채널(VIDEO, PHONE, EMAIL, IN_PERSON, OTHER) 동일, 크기만 상이.

**Self-Challenge**: SC-1(✓) SC-2(✓ 실제 중복) SC-3(✓ 추출 가능) SC-4(✓) SC-5(△ 현재 5개 채널 고정이면 낮은 위험)

---

### [MTL-03] createLog.isError 시 인라인 에러 메시지 텍스트 부재 — [Moderate/HIGH] — Priority: P2

**파일**: `InlineMeetingForm.tsx:61`
**카테고리**: UX / 에러 피드백

**문제**: `createLog.isError` 시 폼 테두리만 빨간색으로 변경됨 (`border-red-300`). 별도 toast가 존재하지만, 인라인 폼 내에 에러 메시지 텍스트가 없어 사용자가 왜 실패했는지 즉시 알기 어려움.

**현재 코드**:
```tsx
className={`rounded border bg-accent/5 p-2 space-y-2 ${
  createLog.isError ? "border-red-300" : "border-accent/30"
}`}
```

**권장 수정**: 폼 하단에 에러 메시지 텍스트 추가:
```tsx
{createLog.isError && (
  <p className="text-xs text-red-500">저장에 실패했습니다. 다시 시도해 주세요.</p>
)}
```

**검증**: Read로 InlineMeetingForm.tsx 확인. isError 조건부 스타일은 있으나 텍스트 메시지 없음 확인.

**Self-Challenge**: SC-1(✓) SC-2(✓ UX 개선 여지 명확) SC-3(✓) SC-4(✓) SC-5(✓)

---

### [MTL-02] daysBetween DST 전환 시 ±1일 오차 가능성 — [Minor/MEDIUM] — Priority: P3

**파일**: `timelineItems.ts:11-15`
**카테고리**: 정확성 (엣지 케이스)

**문제**: `new Date("YYYY-MM-DD")`는 UTC 자정으로 파싱되므로 `Math.round`로 보정되어 있음. 그러나 이론적으로 DST 전환일(한국은 DST 미사용이므로 실질적 영향 없음)에 오차 가능.

**현재 코드**:
```typescript
return Math.round((db.getTime() - da.getTime()) / (1000 * 60 * 60 * 24));
```

**검증**: `Math.round` 사용으로 ±1시간 오차는 흡수됨. 한국 타임존(KST, DST 없음)에서는 실질 문제 없음.

**판정**: 현재 환경에서 실제 버그 발생 확률 극히 낮음. 문서화 수준의 참고 사항.

**Self-Challenge**: SC-1(✓) SC-2(△ 한국 DST 없음) SC-3(✓) SC-4(✓) SC-5(△ 실질 영향 없음) → 신뢰도 MEDIUM으로 하향

---

### [MTL-05] elapsed 필드 설계 기록 — [Minor/MEDIUM] — Priority: P3

**파일**: `timelineItems.ts:26-29`
**카테고리**: 설계 문서화

**문제**: `elapsed` 필드가 `buildTimelineItems` 내에서 인접 stage 간 일수 차이로 계산되는데, 이 로직의 의도(stage-to-stage만 표시, meeting 사이는 생략)가 코드 내 주석으로만 설명됨. 타입 정의에 JSDoc이 없음.

**판정**: 기능적 문제 없음. 향후 유지보수 시 참고 수준.

**Self-Challenge**: SC-1(✓) SC-2(△ 코드 자체가 명확) SC-5(△ 설계 결정은 플랜 문서에 기록됨) → 신뢰도 MEDIUM

---

### [MTL-06] useMemo 의존성 meetingData?.items — [Minor/HIGH] — Priority: P3

**파일**: `MarketingTimelineView.tsx:68`
**카테고리**: 정확성 확인

**문제**: `useMemo` 의존성이 `[meetingData?.items]`로 설정됨. `meetingData` 자체가 아닌 `.items` 속성을 의존성으로 사용하여 불필요한 재계산 방지. 이는 R5 수정에서 의도적으로 변경된 것.

**판정**: 올바른 최적화. 이슈 아님 — 확인 완료.

**Self-Challenge**: SC-1(✓) SC-2(✓ 의도적 설계) SC-3(N/A) SC-4(✓) SC-5(✓)

---

## Priority Matrix

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [MTL-04] [Moderate/HIGH]: handleSubmit isPending 가드 누락 — InlineMeetingForm.tsx (점수: 40)
2. [MTL-01] [Moderate/HIGH]: CHANNEL_ICON 중복 정의 — TimelineMeetingCard.tsx + BuyerMeetingTimeline.tsx (점수: 40)
3. [MTL-03] [Moderate/HIGH]: 인라인 에러 메시지 텍스트 부재 — InlineMeetingForm.tsx (점수: 40)

### P3 — 저우선 (점수: <30, 개선 가능)
1. [MTL-02] [Minor/MEDIUM ⚠️]: daysBetween DST 엣지 케이스 — timelineItems.ts (점수: 12)
2. [MTL-05] [Minor/MEDIUM ⚠️]: elapsed 필드 JSDoc 부재 — timelineItems.ts (점수: 12)
3. [MTL-06] [Minor/HIGH]: useMemo 의존성 확인 완료 — MarketingTimelineView.tsx (점수: 20)

## Methodology

- Agents: code-reviewer (1개)
- Excluded Agents: 없음 (quick 모드)
- Files scanned: 6개
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: 생략 (Critical + Major 0건)
- Backend availability: N/A (FE 전용 리뷰)

## 검증 투명성

### 검증 통계
- 검증한 가설: 13건
- 거부된 가설 (사전 제거): 7건
- 보고된 이슈: 6건
- 거부율: 54%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | "에러 핸들링 없음" → onError 콜백 확인됨 |
| 이미 수정됨 | 2 | R1-R8 수정에서 이미 해결된 항목 |
| 오판 | 1 | 코드 로직 재확인 시 문제 아님 |
| 신뢰도 불충분 | 1 | 증거 약함 |
