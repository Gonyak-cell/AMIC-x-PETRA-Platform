# MA 파이프라인 이전 단계 탭 네비게이션 구현

> 2026-02-24 21:48 | 카테고리: UI | 심각도: UX 개선

## 문제

TransactionWorkspacePage의 워크플로우 파이프라인(1.수임 ~ 7.Post-Closing)에서 이전 단계를 클릭해도 해당 단계의 탭으로 이동할 수 없었음. 항상 현재 단계(예: Post-Closing)의 탭으로 폴백.

**근본 원인**: `PHASE_VISIBLE_TABS[txn.phase]`가 현재 단계의 탭만 포함하여, 이전 단계의 대표 탭(예: "contracts")이 필터링됨.

## 시도한 접근 (실패)

| # | 접근 | 실패 원인 |
|---|------|----------|
| 1 | `PHASE_VISIBLE_TABS` 누적 방식 전환 | 모든 이전 단계 탭이 한꺼번에 표시됨 (POST_CLOSING에서 18개 탭) — UX 파괴 |
| 2 | `viewedPhase` state + `navigate` 동시 호출 | React state와 Router state 간 레이스 컨디션 — 첫 렌더에서 viewedPhase=null 상태로 폴백 |
| 3 | `useRef`로 동기 추적 + useEffect | useEffect 자체가 비동기라 여전히 타이밍 불일치 |

## 최종 해결

**핵심 원칙**: 파이프라인 클릭 시 URL(navigate)을 변경하지 않고, 순수 React state(`viewedPhase`)로만 UI를 제어.

### 변경 파일

**`amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx`**

| 변경 | 라인 | 설명 |
|------|------|------|
| `viewedPhase` state 추가 | 215 | 파이프라인에서 클릭한 단계를 추적 |
| `handleTabChange` 수정 | 344-345 | 탭 직접 클릭 시 `setViewedPhase(null)` — 현재 단계 뷰로 복귀 |
| `effectivePhase` 계산 | 537 | `viewedPhase ?? txn.phase` — 클릭한 단계 우선 |
| `safeActiveTab` 계산 | 542-544 | viewedPhase 있으면 `PHASE_TAB_MAP[viewedPhase]`, 없으면 URL 기반 |
| 리다이렉트 useEffect 제거 | (삭제) | 레이스 컨디션 원인이었던 useEffect 완전 제거 |
| 파이프라인 클릭 핸들러 | 649 | `setViewedPhase(phase)` only — navigate 없음 |
| Tabs prop | 681 | `activeTab={safeActiveTab}` |
| 조건부 렌더링 | 18곳 | `{activeTab ===` → `{safeActiveTab ===` 일괄 교체 |

**`amic-platform/src/modules/ma/constants.ts`** — 변경 없음 (누적 방식 시도 후 원복)

### 동작 흐름

```
파이프라인 "5. 협상" 클릭
  → setViewedPhase("NEGOTIATION")  [React state, 동기]
  → effectivePhase = "NEGOTIATION"
  → visibleTabIds = PHASE_VISIBLE_TABS["NEGOTIATION"] = [..., "contracts"]
  → tabs = NEGOTIATION 단계 탭만 필터
  → safeActiveTab = PHASE_TAB_MAP["NEGOTIATION"] = "contracts"
  → Tabs에 "contracts" 하이라이트 + 계약/SPA 콘텐츠 렌더

탭 바에서 "Overview" 클릭
  → handleTabChange("overview")
  → setViewedPhase(null)  [초기화]
  → navigate("/ma/transactions/${id}")  [URL 변경]
  → effectivePhase = txn.phase (현재 단계)
  → 현재 단계 탭 복원
```

### 설계 결정

- **URL 미반영**: 파이프라인 클릭은 "미리보기" 성격이므로 URL에 반영하지 않음. 새로고침 시 현재 단계 overview로 복귀 — 의도된 동작.
- **미래 단계 무시**: `clickedIdx > currentIdx`이면 return — 아직 도달하지 않은 단계는 클릭 불가.
- **서브탭 미변경**: `buyerSubTab`, `ddSubTab`, `contractSubTab` prop은 별도 state이므로 영향 없음.

## 검증

- `npx tsc --noEmit` 통과
- `{activeTab ===` 잔존 0개
- `viewedPhaseRef` 잔존 0개
- constants.ts 누적 코드 잔존 없음
